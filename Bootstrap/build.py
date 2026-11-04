#!/usr/bin/env python3
"""Cross-build the tiny macOS bootstrap with Zig, then write a universal binary.

Usage: python3 build.py /absolute/path/to/zig
The Zig toolchain is a build dependency only and is not part of the app.
"""
import hashlib
from pathlib import Path
import struct
import subprocess
import sys

root = Path(__file__).resolve().parent
zig = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path('zig')
slices = []
for architecture, cpu_type, cpu_subtype in (
    ('x86_64', 0x01000007, 3),
    ('aarch64', 0x0100000c, 0),
):
    output = root / ('launcher-' + architecture)
    subprocess.run([
        str(zig), 'cc', '-target', architecture + '-macos.11.0',
        '-O2', '-Wall', '-Wextra', '-Werror',
        str(root / 'launcher.c'), '-o', str(output),
    ], check=True)
    blob = output.read_bytes()
    if blob[:4] != b'\xcf\xfa\xed\xfe':
        raise RuntimeError('Expected a 64-bit little-endian Mach-O slice')
    _, actual_cpu, actual_subtype, _, count, commands_size, _, _ = struct.unpack_from('<8I', blob)
    if actual_cpu != cpu_type:
        raise RuntimeError('Unexpected architecture in output')
    command_offset = 32
    signatures = []
    for _ in range(count):
        command, command_size = struct.unpack_from('<II', blob, command_offset)
        if command == 0x1d:
            _, _, offset, size = struct.unpack_from('<4I', blob, command_offset)
            signatures.append({'offset': offset, 'size': size})
            if offset + size > len(blob):
                raise RuntimeError('Signature exceeds file size')
            signature = blob[offset:offset + size]
            signature_count = struct.unpack_from('>I', signature, 8)[0]
            for signature_index in range(signature_count):
                slot, cd = struct.unpack_from('>II', signature, 12 + signature_index * 8)
                if slot != 0:
                    continue
                fields = struct.unpack_from('>9I', signature, cd)
                magic, length, version, flags, hash_offset, identifier_offset, special_count, page_count, code_limit = fields
                hash_size, hash_type, platform, page_shift = struct.unpack_from('>4B', signature, cd + 36)
                if magic != 0xfade0c02 or not (flags & 2) or hash_size != 32 or hash_type != 2:
                    raise RuntimeError('Expected an ad-hoc SHA-256 CodeDirectory')
                page_size = 1 << page_shift
                for page in range(page_count):
                    expected = signature[cd + hash_offset + page * hash_size:cd + hash_offset + (page + 1) * hash_size]
                    actual = hashlib.sha256(blob[page * page_size:min((page + 1) * page_size, code_limit)]).digest()
                    if expected != actual:
                        raise RuntimeError('Ad-hoc code signature page hash mismatch')
        command_offset += command_size
    if command_offset != 32 + commands_size:
        raise RuntimeError('Invalid load-command size')
    if architecture == 'aarch64' and not signatures:
        raise RuntimeError('Apple Silicon slice needs an ad-hoc signature')
    print({'architecture': architecture, 'cpu_subtype': actual_subtype,
           'bytes': len(blob), 'signatures': signatures,
           'sha256': hashlib.sha256(blob).hexdigest()})
    slices.append((cpu_type, actual_subtype, blob))

alignment = 14
boundary = 1 << alignment
def align(n):
    return (n + boundary - 1) & -boundary

header_size = 8 + 20 * len(slices)
position = align(header_size)
headers = []
for cpu_type, cpu_subtype, blob in slices:
    headers.append((cpu_type, cpu_subtype, position, len(blob), alignment))
    position = align(position + len(blob))
fat = bytearray(position)
struct.pack_into('>II', fat, 0, 0xcafebabe, len(slices))
for index, (header, (_, _, blob)) in enumerate(zip(headers, slices)):
    struct.pack_into('>5I', fat, 8 + 20 * index, *header)
    fat[header[2]:header[2] + len(blob)] = blob
output = root / 'GrowtopiaLauncher'
output.write_bytes(fat)
output.chmod(0o755)
print({'universal': str(output), 'bytes': len(fat),
       'sha256': hashlib.sha256(fat).hexdigest()})
