#!/usr/bin/env python3
"""Build the universal macOS app and release archive using Apple's build tools."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "Growtopia Launcher.app"
BUNDLE_ID = "ee.nigol.growtopia.launcher"
MINIMUM_MACOS = "11.0"
RESOURCE_FILES = (
    "core.sh", "dialogs.applescript", "install-ui.sh", "ui.js",
    "README.html", "AppIcon.icns", "cleanup-installers.sh", "trash-file.sh",
    "trash-file.js", "diagnostics.sh",
)


def read_version(root: Path = ROOT) -> str:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version):
        raise ValueError("VERSION must contain one numeric major.minor.patch version")
    return version


def validate_sources(root: Path = ROOT) -> str:
    version = read_version(root)
    required = [root / "Bootstrap" / "launcher.c", root / "LICENSE"]
    required.extend(root / "Resources" / name for name in RESOURCE_FILES)
    for path in required:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing regular source file: {path.relative_to(root)}")
    ui_source = (root / "Resources" / "ui.js").read_text(encoding="utf-8")
    ui_version = re.search(r"\bvar\s+VERSION\s*=\s*['\"]([^'\"]+)['\"]", ui_source)
    if not ui_version or ui_version.group(1) != version:
        raise ValueError("Resources/ui.js VERSION must match the root VERSION file")
    return version


def run(arguments: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(arguments, check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else ""


def source_commit(value: str | None) -> str:
    if value:
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise ValueError("--commit must be the exact 40-character source commit SHA")
        return value
    try:
        candidate = run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture=True)
        return candidate if re.fullmatch(r"[0-9a-f]{40}", candidate) else "unknown"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build(output: Path, commit: str) -> tuple[Path, Path]:
    version = validate_sources()
    if sys.platform != "darwin":
        raise RuntimeError("The release build must run on macOS. Use --validate-only for source checks elsewhere.")
    output.mkdir(parents=True, exist_ok=True)
    output = output.resolve()
    archive = output / f"growtopia-launcher-macos-{version}.zip"
    checksums = output / "SHA256SUMS"
    clang = run(["/usr/bin/xcrun", "--find", "clang"], capture=True)
    sdk = run(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"], capture=True)

    with tempfile.TemporaryDirectory(prefix="growtopia-release-", dir=output) as temporary:
        work = Path(temporary)
        release = work / f"Growtopia-Launcher-{version}"
        app = release / APP_NAME
        contents = app / "Contents"
        macos = contents / "MacOS"
        resources = contents / "Resources"
        macos.mkdir(parents=True)
        resources.mkdir()

        slices = []
        for architecture in ("arm64", "x86_64"):
            binary = work / f"launcher-{architecture}"
            run([
                clang, "-arch", architecture, "-isysroot", sdk,
                f"-mmacosx-version-min={MINIMUM_MACOS}",
                "-O2", "-Wall", "-Wextra", "-Werror",
                str(ROOT / "Bootstrap" / "launcher.c"), "-o", str(binary),
            ])
            slices.append(binary)
        executable = macos / "GrowtopiaLauncher"
        run(["/usr/bin/lipo", "-create", *(str(path) for path in slices), "-output", str(executable)])
        executable.chmod(0o755)
        architectures = set(run(["/usr/bin/lipo", "-archs", str(executable)], capture=True).split())
        if architectures != {"arm64", "x86_64"}:
            raise RuntimeError(f"Unexpected application architectures: {sorted(architectures)}")

        for name in RESOURCE_FILES:
            destination = resources / name
            shutil.copyfile(ROOT / "Resources" / name, destination)
            destination.chmod(0o755 if name.endswith(".sh") else 0o644)
        shutil.copyfile(ROOT / "LICENSE", resources / "LICENSE")
        info = {
            "CFBundleDevelopmentRegion": "en",
            "CFBundleDisplayName": "Growtopia Launcher",
            "CFBundleExecutable": "GrowtopiaLauncher",
            "CFBundleIdentifier": BUNDLE_ID,
            "CFBundleName": "Growtopia Launcher",
            "CFBundleIconFile": "AppIcon",
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": version,
            "CFBundleVersion": version,
            "LSApplicationCategoryType": "public.app-category.utilities",
            "LSMinimumSystemVersion": MINIMUM_MACOS,
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
        }
        (contents / "Info.plist").write_bytes(plistlib.dumps(info))
        (contents / "PkgInfo").write_bytes(b"APPL????")
        run(["/usr/bin/plutil", "-lint", str(contents / "Info.plist")])

        # This seals the local bundle; it is not Developer ID signing or notarization.
        run([
            "/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none",
            "--identifier", BUNDLE_ID, str(app),
        ])
        run(["/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])
        shutil.copyfile(ROOT / "Resources" / "README.html", release / "READ-ME-FIRST.html")
        shutil.copyfile(ROOT / "LICENSE", release / "LICENSE")
        build_info = {
            "application_version": version,
            "source_commit": commit,
            "architectures": sorted(architectures),
            "minimum_macos": MINIMUM_MACOS,
            "build_macos_version": run(["/usr/bin/sw_vers", "-productVersion"], capture=True),
            "build_macos_build": run(["/usr/bin/sw_vers", "-buildVersion"], capture=True),
            "build_architecture": run(["/usr/bin/uname", "-m"], capture=True),
            "compiler": run([clang, "--version"], capture=True).splitlines()[0],
            "signature": "ad-hoc complete application bundle",
            "notarized": False,
            "note": "Build environment only; not a claim of manual game or UI testing.",
        }
        (release / "BUILD-INFO.json").write_text(json.dumps(build_info, indent=2) + "\n", encoding="utf-8")
        staged_archive = work / archive.name
        run([
            "/usr/bin/ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
            str(release), str(staged_archive),
        ])
        os.replace(staged_archive, archive)

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksums.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(json.dumps({"version": version, "archive": str(archive), "sha256": digest, "checksums": str(checksums)}))
    return archive, checksums


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--commit", help="Exact source commit used by the release build")
    parser.add_argument("--validate-only", action="store_true", help="Check source inputs without building")
    args = parser.parse_args()
    version = validate_sources()
    if args.validate_only:
        print(f"Source inputs valid for {version}")
        return
    build(args.output, source_commit(args.commit))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Build failed: {error}") from error
