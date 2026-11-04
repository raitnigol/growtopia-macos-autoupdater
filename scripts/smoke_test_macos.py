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
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        captured = result.stdout + result.stderr
        if result.returncode != 0 or "GROWTOPIA_UI_SMOKE_OK" not in captured:
            if captured:
                print(captured, file=sys.stderr)
            raise RuntimeError(f"Native UI smoke test failed (exit {result.returncode})")
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
