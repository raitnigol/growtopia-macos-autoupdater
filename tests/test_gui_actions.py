"""GUI action contracts, with only platform-specific commands mocked."""
import os
from pathlib import Path
import plistlib
import shlex
import subprocess
import tempfile
import unittest

CORE = Path(__file__).resolve().parents[1] / 'Resources' / 'core.sh'
BASH = os.environ.get('GROWTOPIA_TEST_BASH', '/bin/bash')


class GUIActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='growtopia-gui-')
        self.root = Path(self.tmp.name)
        self.home = self.root / "Rait's Mac"
        self.state = self.home / 'Library' / 'Application Support' / 'Growtopia Launcher'
        self.state.mkdir(parents=True)
        self.run = self.root / 'run'
        self.run.mkdir()
        self.app = self.home / 'Applications' / 'Growtopia.app'
        self.bin = self.root / 'mock-tools'
        self.bin.mkdir()
        self.calls = self.root / 'calls'
        self.mock('uname', '#!/bin/sh\nprintf Darwin\n')
        self.mock('dialog', '#!/bin/sh\nprintf dialog >> "$GT_CALLS"\nexit 97\n')
        self.mock('open', '#!/bin/sh\nprintf "open:%s\\n" "$1" >> "$GT_CALLS"\n')
        self.mock('curl', '''#!/usr/bin/env python3
import os,sys
from pathlib import Path
args=sys.argv[1:]
with open(os.environ['GT_CALLS'],'a') as f:f.write('head\\n' if '--head' in args else 'download\\n')
if '--head' not in args:sys.exit(96)
Path(args[args.index('-D')+1]).write_text('HTTP/1.1 200 OK\\r\\nLast-Modified: Wed, 04 Nov 2026 10:00:00 GMT\\r\\nContent-Length: 1234\\r\\nETag: "gui"\\r\\n\\r\\n')
sys.stdout.write('200')
''')
        self.mock('plistbuddy', '''#!/usr/bin/env python3
import plistlib,shlex,sys
from pathlib import Path
cmd=shlex.split(sys.argv[2]);file=Path(sys.argv[3])
try:
 data=plistlib.loads(file.read_bytes())
 if cmd[0]=='Print':
  value=data[cmd[1].lstrip(':')]
  print(value)
 elif cmd[0]=='Add':
  data[cmd[1].lstrip(':')]=' '.join(cmd[3:])
  file.write_bytes(plistlib.dumps(data))
 else:sys.exit(2)
except (FileNotFoundError,KeyError):sys.exit(1)
''')

    def tearDown(self):
        self.tmp.cleanup()

    def mock(self, name, source):
        p = self.bin / name
        p.write_text(source.replace('#!/usr/bin/env python3', '#!' + os.sys.executable))
        p.chmod(0o755)
        return p

    def installed_app(self):
        (self.app / 'Contents' / 'MacOS').mkdir(parents=True)
        (self.app / 'Contents' / 'Info.plist').write_bytes(plistlib.dumps({
            'CFBundleExecutable': 'Growtopia',
            'CFBundleShortVersionString': '5.61',
            'CFBundleVersion': '561',
        }))
        (self.app / 'Contents' / 'MacOS' / 'Growtopia').write_bytes(b'test fixture')
        (self.state / 'target').write_text(str(self.app))

    def shell(self, mode, extra=''):
        values = {'HOME': self.home, 'STATE': self.state, 'LOG': self.root / 'log',
                  'UNAME': self.bin / 'uname', 'CURL': self.bin / 'curl',
                  'OSASCRIPT': self.bin / 'dialog', 'OPEN': self.bin / 'open',
                  'PLISTBUDDY': self.bin / 'plistbuddy'}
        script = 'source ' + shlex.quote(str(CORE)) + '\n'
        script += '\n'.join(k+'='+shlex.quote(str(v)) for k,v in values.items()) + '\n'
        script += 'running_game() { return 1; }\n'
        script += extra + '\nmain ' + shlex.quote(mode) + ' ' + shlex.quote(str(self.run))
        env = dict(os.environ, GT_CALLS=str(self.calls))
        result = subprocess.run([BASH, '-c', script], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.run / 'result').read_text().strip(), 'ok')
        return plistlib.loads((self.run / 'info.plist').read_bytes())

    def test_inspect_is_head_only_without_trust_or_launch(self):
        self.installed_app()
        info = self.shell('inspect')
        self.assertEqual(self.calls.read_text(), 'head\n')
        self.assertEqual(info['installedVersion'], '5.61')
        self.assertEqual(info['installed'], 'true')
        self.assertEqual(info['remoteSizeBytes'], '1234')
        self.assertEqual(info['downloadedVersion'], '')
        self.assertEqual(info['downloadState'], 'changed')
        self.assertEqual(info['target'], str(self.app))
        self.assertFalse((self.state / 'trust').exists())

    def test_launch_opens_installed_game_without_network_or_trust_prompt(self):
        self.installed_app()
        info = self.shell('launch')
        self.assertEqual(self.calls.read_text(), 'open:' + str(self.app) + '\n')
        self.assertEqual(info['downloadState'], 'unknown')
        self.assertEqual(info['lastCheck'], '')

    def test_cached_update_finishes_without_launching(self):
        self.installed_app()
        (self.state / 'trust').write_text('manual')
        extra = '''
TARGET=$(read_setting target)
write_setting cdn.date 'Wed, 04 Nov 2026 10:00:00 GMT'
write_setting cdn.length 1234
write_setting cdn.etag '"gui"'
write_setting cdn.fingerprint "$(fingerprint "$TARGET")"
'''
        info = self.shell('update', extra)
        self.assertEqual(self.calls.read_text(), 'head\n')
        self.assertEqual(info['downloadState'], 'unchanged')
        self.assertIn('Click Launch Installed', (self.run / 'status').read_text())

    def test_source_choice_is_saved_without_network_or_launch(self):
        info = self.shell('source-website')
        self.assertFalse(self.calls.exists())
        self.assertEqual((self.state / 'source').read_text().strip(), 'website')
        self.assertTrue((self.state / 'force-fresh').exists())
        self.assertEqual(info['source'], 'website')

    def test_trust_choice_is_saved_without_installing(self):
        info = self.shell('trust-official')
        self.assertFalse(self.calls.exists())
        self.assertEqual((self.state / 'trust').read_text().strip(), 'official')
        self.assertTrue((self.state / 'force-fresh').exists())
        self.assertEqual(info['trust'], 'official')

    def test_personal_target_is_saved_without_installing(self):
        info = self.shell('personal-target')
        self.assertFalse(self.calls.exists())
        self.assertEqual((self.state / 'target').read_text().strip(), str(self.app))
        self.assertFalse(self.app.exists())
        self.assertEqual(info['target'], str(self.app))

    def test_fresh_dispatch_sets_flag_without_auto_launch(self):
        info = self.shell('fresh', '''
choose_trust() { TRUST=manual; write_setting trust manual; }
update_and_play() { [[ -f "$STATE/force-fresh" ]]; status 'test update requested'; }
''')
        self.assertFalse(self.calls.exists())
        self.assertTrue((self.state / 'force-fresh').exists())
        self.assertEqual(info['trust'], 'manual')

    def test_update_finish_does_not_open_game_in_fresh_mode(self):
        self.shell('fresh', '''
choose_trust() { TRUST=manual; write_setting trust manual; }
update_and_play() { finish_update; }
''')
        self.assertFalse(self.calls.exists())


if __name__ == '__main__':
    unittest.main()
