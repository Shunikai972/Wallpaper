"""Regression tests for the launcher on machines without the injected workbench."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

LAUNCHER = Path(__file__).resolve().parents[1] / 'scripts/code-launcher.sh'


class LauncherTests(unittest.TestCase):
    def test_system_code_and_arguments_survive_fallback(self):
        with tempfile.TemporaryDirectory(prefix='wallpaper test ') as tmp:
            root = Path(tmp)
            binary = root / 'bin' / 'code'
            binary.parent.mkdir()
            binary.write_text('#!/bin/sh\nprintf "<%s>\\n" "$@"\n')
            binary.chmod(0o755)
            env = dict(os.environ, HOME=str(root), PATH=f'{binary.parent}:/usr/bin:/bin')
            for args in (['--version'], ['a file.txt']):
                proc = subprocess.run(['bash', str(LAUNCHER), *args], env=env, text=True, capture_output=True)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(proc.stdout.strip(), f'<{args[0]}>')
