"""Explicit installer-cleanup selection with the native Trash call mocked."""
from pathlib import Path
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest

WORKER = Path(__file__).resolve().parents[1] / 'Resources' / 'cleanup-installers.sh'
SHELL = os.environ.get('GROWTOPIA_TEST_BASH', '/bin/bash')


class CleanupInstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='gt-cleanup-')
        self.root = Path(self.tmp.name)
        self.resources = self.root / 'app resources'
        self.resources.mkdir()
        self.run = self.root / 'run'
        self.run.mkdir()
        self.downloads = self.root / "Rait's Downloads"
        self.downloads.mkdir()
        self.trash = self.root / 'mock Trash'
        self.trash.mkdir()
        self.calls = self.root / 'trash-calls.jsonl'
        fake_uname = self.resources / 'fake uname'
        fake_uname.write_text('#!/bin/sh\nprintf Darwin\n')
        fake_uname.chmod(0o755)
        text = WORKER.read_text().replace('/usr/bin/uname', shlex.quote(str(fake_uname)))
        self.worker = self.resources / 'cleanup-installers.sh'
        self.worker.write_text(text)
        helper = self.resources / 'trash-file.sh'
        helper.write_text('#!' + sys.executable + '\n' + '''
from pathlib import Path
import json,os,sys
selected=Path(sys.argv[1])
log=Path(os.environ['GT_TRASH_LOG'])
previous=log.read_text().splitlines() if log.exists() else []
with log.open('a') as out:out.write(json.dumps(str(selected))+'\\n')
if str(selected)==os.environ.get('GT_FAIL_PATH'):sys.exit(73)
selected.rename(Path(os.environ['GT_TRASH_DIR'])/(str(len(previous))+'-'+selected.name))
if os.environ.get('GT_CANCEL_AFTER_MOVE')=='1':Path(os.environ['GT_RUN_DIR'],'cancel').touch()
''')
        helper.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def file(self, name, value='installer'):
        path = self.downloads / name
        path.write_text(value)
        return path

    def run_worker(self, selected, success=True, **extra_env):
        env = dict(os.environ, GT_TRASH_LOG=str(self.calls), GT_TRASH_DIR=str(self.trash), GT_RUN_DIR=str(self.run))
        env.update(extra_env)
        result = subprocess.run([SHELL, str(self.worker), *map(str, selected), str(self.run)], cwd=self.root, env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        self.assertEqual((self.run / 'result').read_text().strip(), 'ok' if success else 'error')
        return result

    def attempts(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def test_only_explicitly_selected_matching_file_moves(self):
        selected = self.file('Growtopia.dmg', 'selected')
        unselected = self.file('Growtopia (1).dmg', 'keep-growtopia')
        unrelated = self.file('SomeOtherInstaller.dmg', 'keep-unrelated')
        self.run_worker([selected])
        self.assertFalse(selected.exists())
        self.assertEqual(self.attempts(), [str(selected)])
        self.assertEqual(unselected.read_text(), 'keep-growtopia')
        self.assertEqual(unrelated.read_text(), 'keep-unrelated')
        self.assertEqual([p.read_text() for p in self.trash.iterdir()], ['selected'])
        self.assertIn('Moved 1 installer', (self.run / 'status').read_text())

    def test_multiple_selected_case_variants_move(self):
        first = self.file('growtopia-mac.DMG', 'first')
        second = self.file('GROWTOPIA (2).DmG', 'second')
        self.run_worker([first, second])
        self.assertEqual(self.attempts(), [str(first), str(second)])
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())
        self.assertEqual(sorted(p.read_text() for p in self.trash.iterdir()), ['first', 'second'])

    def test_non_growtopia_selection_is_rejected_before_any_move(self):
        matching = self.file('Growtopia.dmg')
        unrelated = self.file('OtherGame.dmg')
        self.run_worker([matching, unrelated], success=False)
        self.assertTrue(matching.exists())
        self.assertTrue(unrelated.exists())
        self.assertEqual(self.attempts(), [])
        self.assertEqual(list(self.trash.iterdir()), [])
        self.assertIn('Only files named Growtopia', (self.run / 'error.txt').read_text())

    def test_directory_selection_is_rejected_before_any_move(self):
        matching = self.file('Growtopia.dmg')
        directory = self.downloads / 'Growtopia-folder.dmg'
        directory.mkdir()
        self.run_worker([matching, directory], success=False)
        self.assertTrue(matching.exists())
        self.assertTrue(directory.is_dir())
        self.assertEqual(self.attempts(), [])
        self.assertEqual(list(self.trash.iterdir()), [])

    def test_symlink_selection_is_rejected_before_any_move(self):
        matching = self.file('Growtopia.dmg')
        outside = self.root / 'outside-file'
        outside.write_text('keep outside')
        link = self.downloads / 'Growtopia-link.dmg'
        link.symlink_to(outside)
        self.run_worker([matching, link], success=False)
        self.assertTrue(matching.exists())
        self.assertTrue(link.is_symlink())
        self.assertEqual(outside.read_text(), 'keep outside')
        self.assertEqual(self.attempts(), [])

    def test_cancel_before_first_move_preserves_selected_file(self):
        selected = self.file('Growtopia.dmg')
        (self.run / 'cancel').touch()
        self.run_worker([selected])
        self.assertTrue(selected.exists())
        self.assertEqual(self.attempts(), [])
        self.assertIn('stopped after 0', (self.run / 'status').read_text())

    def test_cancel_between_moves_preserves_remaining_selected_file(self):
        first = self.file('Growtopia-first.dmg', 'first')
        second = self.file('Growtopia-second.dmg', 'second')
        self.run_worker([first, second], GT_CANCEL_AFTER_MOVE='1')
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())
        self.assertEqual(self.attempts(), [str(first)])
        self.assertIn('stopped after 1', (self.run / 'status').read_text())
        self.assertIn('remain in Trash', (self.run / 'status').read_text())

    def test_partial_failure_reports_already_moved_count(self):
        first = self.file('Growtopia-first.dmg', 'first')
        second = self.file('Growtopia-second.dmg', 'second')
        third = self.file('Growtopia-third.dmg', 'third')
        self.run_worker([first, second, third], success=False, GT_FAIL_PATH=str(second))
        self.assertFalse(first.exists())
        self.assertEqual(second.read_text(), 'second')
        self.assertEqual(third.read_text(), 'third')
        self.assertEqual(self.attempts(), [str(first), str(second)])
        self.assertEqual([p.read_text() for p in self.trash.iterdir()], ['first'])
        self.assertIn('1 file(s) were already moved', (self.run / 'error.txt').read_text())

    def test_spaces_quotes_and_shell_metacharacters_are_literal(self):
        selected = self.file('Growtopia \'single\' "double" ; $(touch PWNED) `touch ALSO_PWNED` &.dmg', 'literal filename')
        self.run_worker([selected])
        self.assertEqual(self.attempts(), [str(selected)])
        self.assertFalse(selected.exists())
        self.assertEqual([p.read_text() for p in self.trash.iterdir()], ['literal filename'])
        self.assertFalse((self.root / 'PWNED').exists())
        self.assertFalse((self.root / 'ALSO_PWNED').exists())


if __name__ == '__main__':
    unittest.main()
