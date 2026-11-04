#!/usr/bin/env python3
"""Publish verified build assets once; leave existing tags and releases alone."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
import zipfile

from build_macos import ROOT, read_version


def verify_assets(root: Path, assets: Path, version: str, commit: str | None = None) -> tuple[Path, Path, Path]:
    archive = assets / f"growtopia-launcher-macos-{version}.zip"
    checksums = assets / "SHA256SUMS"
    notes = root / "docs" / "releases" / f"v{version}.md"
    for path in (archive, checksums, notes):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing regular release file: {path}")
    expected_line = checksums.read_text(encoding="ascii").strip()
    match = re.fullmatch(r"([0-9a-f]{64})  (growtopia-launcher-macos-[0-9.]+\.zip)", expected_line)
    if not match or match.group(2) != archive.name:
        raise ValueError("SHA256SUMS must describe exactly the expected release archive")
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    if match.group(1) != actual:
        raise ValueError("Release archive checksum does not match SHA256SUMS")
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError("Release archive is corrupt")
        metadata = json.loads(package.read(f"Growtopia-Launcher-{version}/BUILD-INFO.json"))
    if metadata.get("application_version") != version:
        raise ValueError("Packaged build version does not match VERSION")
    if set(metadata.get("architectures", [])) != {"arm64", "x86_64"}:
        raise ValueError("Packaged build does not record both supported architectures")
    if commit is not None and metadata.get("source_commit") != commit:
        raise ValueError("Packaged source commit differs from the release target")
    return archive, checksums, notes


def api_exists(repository: str, endpoint: str, token: str) -> bool:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/{endpoint}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "growtopia-macos-autoupdater-release",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30):
            return True
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise RuntimeError(f"GitHub rejected the lookup (HTTP {error.code}); no release was changed") from error


def publish(repository: str, commit: str, assets: Path, *, dry_run: bool = False) -> bool:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Repository must be in owner/name form")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("The release target must be an exact 40-character source commit SHA")
    version = read_version()
    archive, checksums, notes = verify_assets(ROOT, assets, version, commit)
    tag = f"v{version}"
    arguments = [
        "gh", "release", "create", tag, str(archive), str(checksums),
        "--repo", repository, "--target", commit, "--title", tag,
        "--notes-file", str(notes), "--fail-on-no-commits",
    ]
    if dry_run:
        print(json.dumps({"repository": repository, "tag": tag, "source_commit": commit, "assets": [archive.name, checksums.name], "notes": str(notes)}))
        return False
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is required to publish a release")
    if api_exists(repository, f"releases/tags/{tag}", token):
        print(f"Release {tag} already exists; no files or release metadata were changed.")
        return False
    if api_exists(repository, f"git/ref/tags/{tag}", token):
        print(f"Tag {tag} already exists; no files, tags, or releases were changed.")
        return False
    environment = os.environ.copy()
    environment["GH_TOKEN"] = token
    subprocess.run(arguments, check=True, env=environment)
    print(f"Published {tag} from source commit {commit}.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"), required=not bool(os.environ.get("GITHUB_REPOSITORY")))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--assets", type=Path, default=ROOT / "dist")
    parser.add_argument("--dry-run", action="store_true", help="Validate files without contacting GitHub")
    args = parser.parse_args()
    publish(args.repo, args.commit, args.assets.resolve(), dry_run=args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        raise SystemExit(f"Release failed: {error}") from error
