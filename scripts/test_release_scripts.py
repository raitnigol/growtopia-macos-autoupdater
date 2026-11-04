"""Release safety checks; no GitHub mutations or native builds are performed."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import build_macos
import publish_release

COMMIT = "a" * 40


class ReleaseScriptsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.assets = self.root / "dist"
        self.assets.mkdir()
        (self.root / "VERSION").write_text("2.1.0\n")
        notes = self.root / "docs/releases"
        notes.mkdir(parents=True)
        (notes / "v2.1.0.md").write_text("Release notes\n")
        self.archive = self.assets / "growtopia-launcher-macos-2.1.0.zip"
        self.checksums = self.assets / "SHA256SUMS"
        self.write_archive()

    def tearDown(self):
        self.temporary.cleanup()

    def write_archive(self, source_commit=COMMIT):
        with zipfile.ZipFile(self.archive, "w") as package:
            package.writestr("Growtopia-Launcher-2.1.0/BUILD-INFO.json", json.dumps({
                "application_version": "2.1.0",
                "source_commit": source_commit,
                "architectures": ["arm64", "x86_64"],
            }))
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.checksums.write_text(f"{digest}  {self.archive.name}\n")

    def test_numeric_version_is_read(self):
        self.assertEqual(build_macos.read_version(self.root), "2.1.0")

    def test_version_cannot_inject_release_arguments(self):
        (self.root / "VERSION").write_text("2.1.0\n--draft\n")
        with self.assertRaises(ValueError):
            build_macos.read_version(self.root)

    def test_checksum_and_source_commit_are_verified(self):
        archive, checksums, _ = publish_release.verify_assets(self.root, self.assets, "2.1.0", COMMIT)
        self.assertEqual(archive, self.archive)
        self.assertEqual(checksums, self.checksums)

    def test_changed_archive_is_rejected(self):
        self.archive.write_bytes(self.archive.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            publish_release.verify_assets(self.root, self.assets, "2.1.0", COMMIT)

    def test_wrong_source_commit_is_rejected(self):
        self.write_archive("b" * 40)
        with self.assertRaisesRegex(ValueError, "source commit"):
            publish_release.verify_assets(self.root, self.assets, "2.1.0", COMMIT)

    def test_missing_release_notes_are_rejected(self):
        (self.root / "docs/releases/v2.1.0.md").unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            publish_release.verify_assets(self.root, self.assets, "2.1.0", COMMIT)

    def test_existing_release_is_not_modified(self):
        with patch.object(publish_release, "ROOT", self.root), patch.object(publish_release, "read_version", return_value="2.1.0"), patch.object(publish_release, "api_exists", return_value=True), patch.object(publish_release.subprocess, "run") as command, patch.dict(os.environ, {"GH_TOKEN": "test-token"}):
            self.assertFalse(publish_release.publish("owner/repository", COMMIT, self.assets))
            command.assert_not_called()

    def test_existing_tag_is_not_modified(self):
        with patch.object(publish_release, "ROOT", self.root), patch.object(publish_release, "read_version", return_value="2.1.0"), patch.object(publish_release, "api_exists", side_effect=[False, True]), patch.object(publish_release.subprocess, "run") as command, patch.dict(os.environ, {"GH_TOKEN": "test-token"}):
            self.assertFalse(publish_release.publish("owner/repository", COMMIT, self.assets))
            command.assert_not_called()

    def test_dry_run_does_not_contact_github(self):
        with patch.object(publish_release, "ROOT", self.root), patch.object(publish_release, "read_version", return_value="2.1.0"), patch.object(publish_release, "api_exists") as lookup, patch.object(publish_release.subprocess, "run") as command:
            self.assertFalse(publish_release.publish("owner/repository", COMMIT, self.assets, dry_run=True))
            lookup.assert_not_called()
            command.assert_not_called()

    def test_creation_uses_exact_commit_and_verified_assets(self):
        with patch.object(publish_release, "ROOT", self.root), patch.object(publish_release, "read_version", return_value="2.1.0"), patch.object(publish_release, "api_exists", side_effect=[False, False]), patch.object(publish_release.subprocess, "run") as command, patch.dict(os.environ, {"GH_TOKEN": "test-token"}):
            self.assertTrue(publish_release.publish("owner/repository", COMMIT, self.assets))
            arguments = command.call_args.args[0]
            self.assertEqual(arguments[arguments.index("--target") + 1], COMMIT)
            self.assertIn(str(self.archive), arguments)
            self.assertIn(str(self.checksums), arguments)


if __name__ == "__main__":
    unittest.main()
