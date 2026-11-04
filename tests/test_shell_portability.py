"""Bash 3.2 compatibility regressions for the native app's worker."""
from pathlib import Path
import os
import subprocess
import unittest

CORE = Path(__file__).resolve().parents[1] / 'Resources' / 'core.sh'
SHELL = os.environ.get('GROWTOPIA_TEST_BASH', '/bin/bash')

class ShellPortabilityTests(unittest.TestCase):
    def test_shell_source_is_ascii(self):
        CORE.read_bytes().decode('ascii')

    def test_worker_parses_with_selected_shell(self):
        result = subprocess.run([SHELL, '-n', str(CORE)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

if __name__ == '__main__':
    unittest.main()
