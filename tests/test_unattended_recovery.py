"""Reading controller usage never leaves an unattended Claude session waiting on a human.

A hook `ask` stalls a desktop session with no one at the screen. Usage text runs
without a prompt; recovery of stopped work keeps its host approval, and `--help`
cannot launder a real call. Disposable repos and an isolated session registry only.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d
import git_delivery as g
import ownership
import safety


class UnattendedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(patch.object(ownership, 'REGISTRY', self.base / 'sessions'))
        self.enterContext(patch.dict(os.environ, {'VEERA_HOST': 'claude'}))
        self.original = self.base / 'repo'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.original)], check=True)
        g.git(self.original, 'config', 'user.email', 'fixture@example.invalid')
        g.git(self.original, 'config', 'user.name', 'Fixture')
        (self.original / 'app.py').write_text('value = 1\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-m', 'Fixture baseline')
        self.session_id = 'fixture-unattended-owner'
        metadata = g.workspace(self.original, 'recover', self.session_id)
        self.root = Path(metadata['root'])
        self.capability = metadata['capability_file']
        contract = {'scope': ['app.py'], 'criteria': [{'id': 'C1', 'text': 'Test', 'checks': ['test']}], 'checks': [{'id': 'test', 'kind': 'static', 'argv': ['true']}]}
        d.init(self.root, 'build', 'recovery fixture', contract, 5)
        self.script = str(Path(d.__file__).resolve())

    def hook(self, command, cwd=None):
        payload = {'session_id': self.session_id, 'cwd': str(cwd or self.original), 'tool_name': 'Bash', 'tool_input': {'command': command}}
        return safety.evaluate(payload)

    def owned(self, operation, capability=None):
        return (f'python3 {self.script} {operation} --root {self.root} --session-id {self.session_id} '
                f'--capability-file {capability or self.capability} --file {self.root / ".veera-artifacts" / "report.json"}')

    def test_usage_text_never_prompts(self):
        for command in (f'python3 {self.script} correct-check-reporting --help', f'python3 {self.script} resume -h',
                        f'python3 {self.script} --help'):
            for cwd in (self.original, self.root):
                with self.subTest(command=command, cwd=str(cwd)):
                    self.assertIsNone(self.hook(command, cwd))

    def test_recovery_of_stopped_work_still_asks(self):
        for operation in ('resume', 'amend', 'extend-repairs', 'correct-check-reporting', 'rebind-check-inputs', 'blocker-human-resolve'):
            with self.subTest(operation=operation):
                self.assertTrue(self.hook(self.owned(operation)).startswith('ASK:'))
        # A trailing --help cannot launder a real call carrying arguments.
        self.assertTrue(self.hook(f'python3 {self.script} resume --root {self.root} --help').startswith('ASK:'))

    def test_identity_and_shell_chains_still_refused(self):
        reason = self.hook(self.owned('correct-check-reporting', capability=self.base / 'forged.json'))
        self.assertIsNotNone(reason)
        self.assertFalse(reason.startswith('ASK:'))
        for command in (f'python3 {self.script} correct-check-reporting --help && rm -rf {self.original}',
                        self.owned('amend') + f'; rm -rf {self.original}'):
            with self.subTest(command=command):
                self.assertIsNotNone(self.hook(command))


if __name__ == '__main__':
    unittest.main()
