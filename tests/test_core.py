#!/usr/bin/env python3
"""Portable behavior tests; macOS commands and UI require testing on a Mac."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

CORE = Path(__file__).resolve().parents[1] / 'Resources' / 'core.sh'

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gt-test-')
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.state = self.root / 'state'
        self.work = self.root / 'work'
        self.run_dir = self.root / 'run'
        self.apps = self.home / 'Applications'
        self.stage = self.apps / '.stage'
        self.target = self.apps / 'Growtopia.app'
        self.backup = self.apps / '.Growtopia.previous.app'
        for folder in (self.home, self.state, self.work, self.run_dir, self.apps, self.stage):
            folder.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp.cleanup()

    def shell(self, script, success=True):
        values = dict(HOME=self.home, STATE=self.state, WORK=self.work, RUN_DIR=self.run_dir, TARGET=self.target, STAGE=self.stage)
        prelude = 'source ' + shlex.quote(str(CORE)) + '\n'
        prelude += '\n'.join(f'{k}={shlex.quote(str(v))}' for k,v in values.items())
        prelude += '\nensure_not_running() { :; }\n'
        result = subprocess.run([os.environ.get('GROWTOPIA_TEST_BASH', '/bin/bash'), '-c', prelude+script], text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)
        return result

    @staticmethod
    def app(path, marker):
        path.mkdir(parents=True)
        (path / 'version').write_text(marker)

    def test_url_allowlist_accepts_only_exact_https_hosts(self):
        self.shell('''
for url in https://ubistatic-a.akamaihd.net/0098/file.dmg https://growtopiagame.com/Growtopia-mac.dmg https://www.growtopiagame.com/file; do allowed_url "$url"; done
for url in http://growtopiagame.com/file https://growtopiagame.com.evil.example/file https://growtopiagame.com@evil.example/file https://evil.example/growtopiagame.com/file https://growtopiagame.com:8443/file; do
 if allowed_url "$url"; then exit 90; fi
done
''')

    def test_version_order_handles_numeric_components(self):
        self.shell('''
version_is_lower 5.58 5.61
version_is_lower 5.9 5.10
version_is_lower 5.61 5.61.1
for pair in '5.61 5.58' '5.61 5.61.0' '5.61-beta 5.61' 'unknown 5.61' '5.61 5.9'; do
 set -- $pair
 if version_is_lower "$1" "$2"; then exit 91; fi
done
''')

    def test_header_values_strip_crlf_and_ignore_case(self):
        (self.work / 'headers').write_bytes(b'HTTP/1.1 200 OK\r\nlAsT-mOdIfIeD: Sun, 01 Nov 2026 06:06:26 GMT\r\nContent-Length: 340070658\r\nETag: "abc"\r\n\r\n')
        self.shell('''
[[ "$(header_value "$WORK/headers" last-modified)" = 'Sun, 01 Nov 2026 06:06:26 GMT' ]]
[[ "$(header_value "$WORK/headers" content-length)" = 340070658 ]]
[[ "$(header_value "$WORK/headers" etag)" = '"abc"' ]]
''')

    def test_successful_commit_keeps_previous_game(self):
        self.app(self.target, 'current'); self.app(self.backup, 'older'); self.app(self.stage / 'Growtopia.app', 'new')
        self.shell('commit_stage')
        self.assertEqual((self.target / 'version').read_text(), 'new')
        self.assertEqual((self.backup / 'version').read_text(), 'current')
        self.assertEqual((self.work / 'older-backup.app' / 'version').read_text(), 'older')
        self.assertFalse((self.state / 'transaction-target').exists())

    def test_first_install_does_not_create_fake_previous(self):
        self.app(self.stage / 'Growtopia.app', 'new')
        self.shell('commit_stage')
        self.assertEqual((self.target / 'version').read_text(), 'new')
        self.assertFalse(self.backup.exists())

    def test_final_rename_failure_restores_game_and_old_backup(self):
        self.app(self.target, 'current'); self.app(self.backup, 'older'); self.app(self.stage / 'Growtopia.app', 'new')
        self.shell('''
mv() {
 if [[ "$1" = "$STAGE/Growtopia.app" && "$2" = "$TARGET" ]]; then return 73; fi
 command mv "$@"
}
commit_stage
''', success=False)
        self.assertEqual((self.target / 'version').read_text(), 'current')
        self.assertEqual((self.backup / 'version').read_text(), 'older')
        self.assertFalse((self.state / 'transaction-target').exists())

    def test_current_rename_failure_preserves_game_and_backup(self):
        self.app(self.target, 'current'); self.app(self.backup, 'older'); self.app(self.stage / 'Growtopia.app', 'new')
        self.shell('''
mv() {
 if [[ "$1" = "$TARGET" && "$2" = "${TARGET%/*}/.Growtopia.previous.app" ]]; then return 73; fi
 command mv "$@"
}
commit_stage
''', success=False)
        self.assertEqual((self.target / 'version').read_text(), 'current')
        self.assertEqual((self.backup / 'version').read_text(), 'older')

    def test_symlink_backup_is_refused(self):
        self.app(self.target, 'current'); self.app(self.stage / 'Growtopia.app', 'new')
        outside = self.root / 'outside'; self.app(outside, 'unrelated'); self.backup.symlink_to(outside, target_is_directory=True)
        self.shell('commit_stage', success=False)
        self.assertEqual((self.target / 'version').read_text(), 'current')
        self.assertEqual((outside / 'version').read_text(), 'unrelated')

    def test_cancel_before_commit_keeps_current(self):
        self.app(self.target, 'current'); self.app(self.stage / 'Growtopia.app', 'new'); (self.run_dir / 'cancel').touch()
        self.shell('commit_stage')
        self.assertEqual((self.target / 'version').read_text(), 'current')
        self.assertFalse(self.backup.exists())

    def test_recovery_restores_missing_current(self):
        self.app(self.backup, 'current'); (self.state / 'transaction-target').write_text(str(self.target)+'\n')
        self.shell('recover_transaction')
        self.assertEqual((self.target / 'version').read_text(), 'current')
        self.assertFalse((self.state / 'transaction-target').exists())

    def test_recovery_keeps_completed_current(self):
        self.app(self.target, 'new'); self.app(self.backup, 'current'); (self.state / 'transaction-target').write_text(str(self.target)+'\n')
        self.shell('recover_transaction')
        self.assertEqual((self.target / 'version').read_text(), 'new')
        self.assertEqual((self.backup / 'version').read_text(), 'current')

    def test_recovery_refuses_different_journal_target(self):
        (self.state / 'transaction-target').write_text('/elsewhere/Growtopia.app\n')
        self.shell('recover_transaction', success=False)
        self.assertTrue((self.state / 'transaction-target').exists())

    def test_cache_requires_all_signals_and_matching_install(self):
        self.app(self.target, 'current')
        self.shell('''
SOURCE=cdn; REMOTE_DATE=date; REMOTE_LENGTH=123; REMOTE_ETAG=etag
fingerprint() { printf same; }
write_setting cdn.date date; write_setting cdn.length 123; write_setting cdn.etag etag; write_setting cdn.fingerprint same
cache_matches
REMOTE_ETAG=changed
if cache_matches; then exit 92; fi
REMOTE_ETAG=etag
touch "$STATE/force-fresh"
if cache_matches; then exit 93; fi
rm "$STATE/force-fresh"
fingerprint() { printf changed; }
if cache_matches; then exit 94; fi
fingerprint() { printf same; }
REMOTE_DATE=
if cache_matches; then exit 95; fi
''')

    def test_cache_is_bound_to_selected_source(self):
        self.app(self.target, 'current')
        self.shell('''
SOURCE=website; REMOTE_DATE=date; REMOTE_LENGTH=123; REMOTE_ETAG=
fingerprint() { printf same; }
write_setting cdn.date date; write_setting cdn.length 123; write_setting cdn.etag ''; write_setting cdn.fingerprint same
if cache_matches; then exit 96; fi
''')

    def test_live_lock_is_not_removed(self):
        (self.state / 'lock').mkdir(); (self.state / 'lock' / 'pid').write_text(str(os.getpid())+'\n')
        self.shell('acquire_lock', success=False)
        self.assertEqual((self.state / 'lock' / 'pid').read_text().strip(), str(os.getpid()))

    def test_stale_lock_can_be_recovered(self):
        (self.state / 'lock').mkdir(); (self.state / 'lock' / 'pid').write_text('99999999\n')
        self.shell('acquire_lock; [[ "$LOCK_OWNED" = 1 ]]')
        self.assertNotEqual((self.state / 'lock' / 'pid').read_text().strip(), '99999999')

    def test_unsafe_destination_is_refused(self):
        self.shell('TARGET=/tmp/not-growtopia.app; validate_target', success=False)

    def test_symlink_destination_is_refused(self):
        outside = self.root / 'outside'; self.app(outside, 'unrelated'); self.target.symlink_to(outside, target_is_directory=True)
        self.shell('validate_target', success=False)
        self.assertEqual((outside / 'version').read_text(), 'unrelated')

if __name__ == '__main__':
    unittest.main(verbosity=2)
