"""Exercise the complete self-install worker with platform tools mocked."""
from pathlib import Path
import os
import plistlib
import shlex
import subprocess
import sys
import tempfile
import unittest

WORKER = Path(__file__).resolve().parents[1] / 'Resources' / 'install-ui.sh'
SHELL = os.environ.get('GROWTOPIA_TEST_BASH', '/bin/bash')
BUNDLE_ID = 'ee.nigol.growtopia.launcher'


class SelfInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='gt-self-install-')
        self.root = Path(self.tmp.name)
        self.home = self.root / "Rait's Mac"
        self.home.mkdir()
        self.run = self.root / 'run'
        self.run.mkdir()
        self.source = self.root / 'Downloaded Launcher.app'
        self.destdir = self.home / 'Applications'
        self.dest = self.destdir / 'Growtopia Launcher.app'
        self.tools = self.root / 'tools'
        self.tools.mkdir()
        self.app(self.source, BUNDLE_ID, 'new')
        self.tool('uname', '#!/bin/sh\nprintf Darwin\n')
        self.tool('plistbuddy', '''import plistlib,sys
try:
 print(plistlib.load(open(sys.argv[-1],'rb'))['CFBundleIdentifier'])
except (FileNotFoundError,KeyError):sys.exit(1)
''')
        self.tool('ditto', '''from pathlib import Path
import shutil,sys
shutil.copytree(sys.argv[-2],sys.argv[-1],symlinks=True)
''')
        self.tool('plutil', '''import plistlib,sys
plistlib.load(open(sys.argv[-1],'rb'))
''')
        source = WORKER.read_text()
        for name, original in [('uname','/usr/bin/uname'), ('plistbuddy','/usr/libexec/PlistBuddy'), ('ditto','/usr/bin/ditto'), ('plutil','/usr/bin/plutil')]:
            source = source.replace(original, shlex.quote(str(self.tools / name)))
        self.script = self.root / 'worker.sh'
        self.script.write_text(source)

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, name, source):
        if not source.startswith('#!'):
            source = '#!' + sys.executable + '\n' + source
        p = self.tools / name
        p.write_text(source)
        p.chmod(0o755)

    @staticmethod
    def app(path, identity, marker):
        (path / 'Contents' / 'MacOS').mkdir(parents=True)
        (path / 'Contents' / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': identity}))
        executable = path / 'Contents' / 'MacOS' / 'GrowtopiaLauncher'
        executable.write_text('#!/bin/sh\nexit 0\n')
        executable.chmod(0o755)
        (path / 'marker').write_text(marker)

    def execute(self, success=True, fail_final_rename=False):
        env = dict(os.environ, HOME=str(self.home))
        if fail_final_rename:
            init = self.root / 'bash-init'
            init.write_text('''mv() {
 if [[ "$1" = "$STAGE/new.app" && "$2" = "$DEST_APP" ]]; then return 73; fi
 command mv "$@"
}
''')
            env['BASH_ENV'] = str(init)
        result = subprocess.run([SHELL, str(self.script), str(self.source), str(self.run)], env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        self.assertEqual((self.run / 'result').read_text().strip(), 'ok' if success else 'error')
        return result

    def test_first_install_copies_app_and_preserves_source(self):
        self.execute()
        self.assertEqual((self.dest / 'marker').read_text(), 'new')
        self.assertTrue((self.dest / 'Contents' / 'MacOS' / 'GrowtopiaLauncher').stat().st_mode & 0o111)
        self.assertEqual((self.source / 'marker').read_text(), 'new')
        self.assertEqual(list(self.destdir.glob('.growtopia-ui-install.*')), [])

    def test_same_bundle_identity_can_be_replaced(self):
        self.app(self.dest, BUNDLE_ID, 'old')
        self.execute()
        self.assertEqual((self.dest / 'marker').read_text(), 'new')
        self.assertEqual(list(self.destdir.glob('.growtopia-ui-install.*')), [])

    def test_foreign_destination_is_preserved(self):
        self.app(self.dest, 'org.example.unrelated', 'unrelated')
        self.execute(success=False)
        self.assertEqual((self.dest / 'marker').read_text(), 'unrelated')
        self.assertIn('different app', (self.run / 'error.txt').read_text())

    def test_symlink_destination_app_is_preserved(self):
        outside = self.root / 'outside.app'
        self.app(outside, BUNDLE_ID, 'outside')
        self.destdir.mkdir()
        self.dest.symlink_to(outside, target_is_directory=True)
        self.execute(success=False)
        self.assertTrue(self.dest.is_symlink())
        self.assertEqual((outside / 'marker').read_text(), 'outside')

    def test_symlink_destination_folder_is_preserved(self):
        outside = self.root / 'outside-folder'
        outside.mkdir()
        marker = outside / 'untouched'
        marker.write_text('keep')
        self.destdir.symlink_to(outside, target_is_directory=True)
        self.execute(success=False)
        self.assertTrue(self.destdir.is_symlink())
        self.assertEqual(marker.read_text(), 'keep')
        self.assertFalse((outside / self.dest.name).exists())

    def test_failed_final_rename_restores_old_launcher(self):
        self.app(self.dest, BUNDLE_ID, 'old')
        self.execute(success=False, fail_final_rename=True)
        self.assertEqual((self.dest / 'marker').read_text(), 'old')
        self.assertEqual((self.source / 'marker').read_text(), 'new')
        self.assertEqual(list(self.destdir.glob('.growtopia-ui-install.*')), [])

    def test_unexpected_source_identity_is_rejected(self):
        (self.source / 'Contents' / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'org.example.wrong'}))
        self.execute(success=False)
        self.assertFalse(self.dest.exists())
        self.assertIn('unexpected identity', (self.run / 'error.txt').read_text())


if __name__ == '__main__':
    unittest.main()
