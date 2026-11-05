#!/usr/bin/env python3
"""Open and close the packaged native UI in smoke-test mode; no game is run."""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile

from build_macos import ROOT, read_version


def print_diagnostics(log: Path, offset: int, stdout=None, stderr=None) -> None:
    for label, output in (("UI stdout", stdout), ("UI stderr", stderr)):
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        if output:
            print(f"--- {label} ---\n{output[-32768:]}", file=sys.stderr)
    print("--- Launcher startup log from this test (last 32 KiB) ---", file=sys.stderr)
    try:
        with log.open("rb") as handle:
            end = handle.seek(0, 2)
            start = offset if end >= offset else 0
            handle.seek(max(start, end - 32768))
            output = handle.read().decode("utf-8", errors="replace")
        print(output or "No new startup log entries were written.", file=sys.stderr)
    except OSError as error:
        print(f"Startup log unavailable: {error}", file=sys.stderr)


def run_ui(command: list[str], log: Path, timeout: float = 30) -> None:
    try:
        offset = log.stat().st_size
    except OSError:
        offset = 0
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as error:
        print_diagnostics(log, offset, error.stdout, error.stderr)
        raise RuntimeError(f"Native UI smoke test timed out after {timeout:g} seconds; see diagnostics above") from error
    captured = result.stdout + result.stderr
    if result.returncode != 0 or "GROWTOPIA_UI_SMOKE_OK" not in captured:
        print_diagnostics(log, offset, result.stdout, result.stderr)
        raise RuntimeError(f"Native UI smoke test failed (exit {result.returncode}; success marker required)")


def smoke_test(archive: Path) -> None:
    if sys.platform != "darwin":
        raise RuntimeError("The native UI smoke test requires macOS")
    version = read_version()
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError("The release archive is corrupt")
        for item in package.infolist():
            relative = PurePosixPath(item.filename)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("The archive contains an unsafe path")
            if ((item.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError("The smoke-test archive must not contain symbolic links")
    with tempfile.TemporaryDirectory(prefix="growtopia-ui-smoke-") as temporary:
        destination = Path(temporary)
        subprocess.run(["/usr/bin/ditto", "-x", "-k", str(archive.resolve()), str(destination)], check=True)
        app = destination / f"Growtopia-Launcher-{version}" / "Growtopia Launcher.app"
        resources = app / "Contents" / "Resources"
        if not (resources / "ui.js").is_file():
            raise ValueError("Packaged UI is missing")
        subprocess.run(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)], check=True)
        command = [
            "/usr/bin/osascript", "-l", "JavaScript", str(resources / "ui.js"),
            str(resources), "--smoke-test",
        ]
        run_ui(command, Path.home() / "Library/Logs/Growtopia Launcher UI.log")
    print("Native AppKit/JXA window smoke test passed. No network check, game download, or game launch was requested.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    archive = args.archive or ROOT / "dist" / f"growtopia-launcher-macos-{read_version()}.zip"
    smoke_test(archive)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError, subprocess.TimeoutExpired, zipfile.BadZipFile) as error:
        raise SystemExit(f"Smoke test failed: {error}") from error
