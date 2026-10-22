"""Isolation tests use disposable repos and an isolated session registry only."""
import contextlib
import io
import json
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
from session_fixture import bind


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.base = Path(self.temp)
        self.root = self.base / 'task'
        self.root.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / 'app.py').write_text('value = 1\n')
        contract = {'scope': ['app.py'], 'criteria': [{'id': 'C1', 'text': 'Test', 'checks': ['test']}], 'checks': [{'id': 'test', 'kind': 'static', 'argv': ['true']}]}
        self.state = d.init(self.root, 'fix', 'isolated fixture', contract, 1)
        self.session_id, self.capability = bind(self, self.root)

    def test_unbound_sessions_never_touch_project_state(self):
        before = (self.root / '.veera/state.json').read_bytes()
        for cwd in (self.root, self.root / 'nested', self.base / 'foreign'):
            with self.subTest(cwd=str(cwd)), patch.object(safety, 'status', side_effect=AssertionError('unowned state read')), patch.object(Path, 'resolve', side_effect=AssertionError('unowned cwd resolution')):
                self.assertIsNone(safety.evaluate({'session_id': 'unrelated-session', 'cwd': str(cwd), 'tool_name': 'Bash', 'tool_input': {'command': 'git push'}}))
        self.assertEqual(before, (self.root / '.veera/state.json').read_bytes())

    def test_missing_identity_does_not_adopt_run(self):
        with patch.object(ownership, 'lookup', side_effect=AssertionError('lookup without identity')):
            self.assertIsNone(safety.evaluate({'cwd': str(self.root), 'tool_name': 'Edit'}))

    def test_owner_wrong_project_and_nested_repo_blocked_before_state(self):
        nested = self.root / 'nested'
        nested.mkdir()
        (nested / '.git').mkdir()
        for cwd in (self.base, nested):
            with patch.object(safety, 'status', side_effect=AssertionError('wrong project access')):
                reason = safety.evaluate({'session_id': self.session_id, 'cwd': str(cwd), 'tool_name': 'Edit'})
                self.assertIsNotNone(reason)

    def test_owner_scope_still_enforced(self):
        reason = safety.evaluate({'session_id': self.session_id, 'cwd': str(self.root), 'tool_name': 'Edit', 'tool_input': {'file_path': str(self.root / 'outside.py')}})
        self.assertIn('outside the frozen scope', reason)

    def test_foreign_cli_denied_before_state_or_subprocess(self):
        cases = [('status', []), ('fingerprint', []), ('archive', []), ('dashboard', []), ('init', ['--mode', 'fix', '--request', 'x', '--contract', '/never/read']), ('context-import', ['--file', '/never/read']), ('publish', [])]
        for command, extra in cases:
            with self.subTest(command=command), patch.object(sys, 'argv', ['delivery', command, '--root', str(self.root), '--session-id', 'foreign', '--capability-file', self.capability, *extra]), patch.object(d, 'storage', side_effect=AssertionError('storage')), patch.object(d, 'read_json', side_effect=AssertionError('input read')), patch.object(subprocess, 'run', side_effect=AssertionError('subprocess')), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    d.main()
                self.assertEqual(result.exception.code, 2)

    def test_wrong_capability_and_root_do_not_inspect_workspace(self):
        for root, capability in ((self.base / 'other', self.capability), (self.root, '/wrong')):
            with self.assertRaises(ValueError):
                ownership.authorize(self.session_id, root, capability)

    def test_workspace_creation_preserves_shared_config_and_excludes(self):
        original = self.base / 'original'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(original)], check=True)
        g.git(original, 'config', 'user.name', 'Fixture')
        g.git(original, 'config', 'user.email', 'fixture@example.invalid')
        (original / 'source.txt').write_text('source')
        g.git(original, 'add', '.')
        g.git(original, 'commit', '-m', 'baseline')
        config = (original / '.git/config').read_bytes()
        exclude = (original / '.git/info/exclude').read_bytes()
        index = (original / '.git/index').read_bytes()
        result = g.workspace(original, 'separate', 'separate-owner')
        self.assertEqual(config, (original / '.git/config').read_bytes())
        self.assertEqual(exclude, (original / '.git/info/exclude').read_bytes())
        # git status may refresh index stat data; source and index tree are unchanged.
        self.assertEqual(g.git(original, 'diff', '--cached', '--name-only'), '')
        self.assertEqual((original / 'source.txt').read_text(), 'source')
        self.assertEqual(result['session_id'], 'separate-owner')
        self.assertIsNone(ownership.lookup('unrelated-session'))

    def test_read_scope_and_shell_approval(self):
        payload = {'session_id': self.session_id, 'cwd': str(self.root), 'tool_name': 'Read', 'tool_input': {'file_path': str(self.base / 'foreign.txt')}}
        self.assertIsNotNone(safety.evaluate(payload))
        payload['tool_name'] = 'Bash'
        payload['tool_input'] = {'command': 'python3 other.py'}
        self.assertTrue(safety.evaluate(payload).startswith('ASK:'))

    def test_owner_can_prepare_contract_before_init(self):
        # Owned setup must not mutate/create state merely to permit preparation.
        (self.root / '.veera/state.json').unlink()
        payload = {'session_id': self.session_id, 'cwd': str(self.root), 'tool_name': 'Write', 'tool_input': {'file_path': str(self.root / '.veera-artifacts/contract.json')}}
        with patch.object(safety, 'status', side_effect=AssertionError('premature state access')):
            self.assertIsNone(safety.evaluate(payload))
        self.assertFalse((self.root / '.veera/state.json').exists())

    def test_unbind_only_own_completed_task(self):
        with self.assertRaises(ValueError):
            ownership.unbind(self.session_id, self.root, self.capability)
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state['status'] = 'complete'
            d.save(directory, state)
        ownership.unbind(self.session_id, self.root, self.capability)
        self.assertIsNone(ownership.lookup(self.session_id))
        self.assertTrue((self.root / '.veera/state.json').exists())

    def test_nested_evidence_repository_write_never_allowed(self):
        nested = self.root / '.veera-artifacts/peer'
        nested.mkdir(parents=True)
        (nested / '.git').mkdir()
        payload = {'session_id': self.session_id, 'cwd': str(self.root), 'tool_name': 'Write', 'tool_input': {'file_path': str(nested / 'source.py')}}
        self.assertIn('nested project', safety.evaluate(payload))
        d.stop(self.root, 'stop')
        self.assertIn('nested project', safety.evaluate(payload))

    def test_recovery_approval_independent_of_owner_option_order(self):
        script = str(Path(d.__file__))
        owner = f'--session-id {self.session_id} --capability-file {self.capability}'
        for operation in ('resume', 'blocker-human-resolve'):
            for command in (f'python3 {script} {operation} --root {self.root} {owner} --file approval.json', f'python3 {script} {operation} --root {self.root} --file approval.json {owner}'):
                payload = {'session_id': self.session_id, 'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}}
                self.assertTrue(safety.evaluate(payload).startswith('ASK:'))
        d.stop(self.root, 'stop')
        for command in (f'python3 {script} checkpoint --root {self.root} {owner} --reason checkpoint', f'python3 {script} checkpoint --root {self.root} --reason checkpoint {owner}'):
            payload = {'session_id': self.session_id, 'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}}
            self.assertIsNone(safety.evaluate(payload))
            payload['tool_input']['command'] += '; touch /outside'
            self.assertIsNotNone(safety.evaluate(payload))

    def test_tracked_reserved_source_rejected(self):
        g.git(self.root, 'add', '-f', '.veera/state.json')
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root)


if __name__ == '__main__':
    unittest.main()
