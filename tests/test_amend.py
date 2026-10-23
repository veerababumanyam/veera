"""Amendment regression tests use only disposable tasks and session registries."""
import copy
import json
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
from session_fixture import cli


class AmendmentTests(unittest.TestCase):
    def setUp(self):
        base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(ownership, 'REGISTRY', base / 'sessions'))
        original = base / 'app'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(original)], check=True)
        g.git(original, 'config', 'user.email', 'fixture@example.invalid')
        g.git(original, 'config', 'user.name', 'Fixture')
        (original / 'app.py').write_text('value = 1\n')
        (original / 'helper.py').write_text('value = 1\n')
        g.git(original, 'add', 'app.py', 'helper.py')
        g.git(original, 'commit', '-qm', 'Fixture')
        self.session_id = 'fixture-amend'
        workspace = g.workspace(original, 'amend', self.session_id)
        self.root = Path(workspace['root'])
        self.capability = workspace['capability_file']
        contract = {'delivery_mode': 'local-verify', 'scope': ['app.py'], 'criteria': [{'id': 'C1', 'text': 'Original behavior', 'checks': ['unit']}], 'checks': [{'id': 'unit', 'kind': 'test', 'argv': [sys.executable, '-c', "print('Ran 1 test')"], 'count_pattern': r'Ran (\d+) test', 'timeout_seconds': 2}], 'max_repairs': 2}
        d.init(self.root, 'fix', 'Fixture amendment', contract, 1, 2)
        d.stop(self.root, 'Fixture interruption')
        self.before = d.checkpoint(self.root, 'Fixture checkpoint')
        self.report = {'run_id': self.before['run_id'], 'checkpoint_id': self.before['checkpoint']['id'], 'expected_contract_hash': self.before['contract_hash'], 'authorization': 'Fixture user message reference #17', 'reason': 'Helper needed for original outcome', 'add_scope': ['helper.py'], 'add_criteria': [{'id': 'C2', 'text': 'Helper behavior', 'checks': ['helper']}], 'add_checks': [{'id': 'helper', 'kind': 'test', 'argv': [sys.executable, '-c', "print('Ran 2 tests')"], 'count_pattern': r'Ran (\d+) test', 'timeout_seconds': 2}]}

    def assert_rejected(self, report=None, pattern='.'):
        before = (self.root / '.veera/state.json').read_bytes()
        with self.assertRaisesRegex(d.DeliveryError, pattern):
            d.amend(self.root, self.report if report is None else report)
        self.assertEqual(before, (self.root / '.veera/state.json').read_bytes())

    def test_public_amend_preserves_history_budget_binding_and_resumes(self):
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state.update(repairs=1, checks={'unit': {'status': 'failed', 'test_count': 0}}, review={'approved': False}, usage={'cost_usd': 12}, repair_escalation={'reason': 'fixture'})
            d.event(state, 'check', {'status': 'failed', 'test_count': 0})
            d.save(directory, state)
        before = d.status(self.root)
        owner_bytes = Path(self.capability).read_bytes()
        source = d.snapshot(self.root)
        report_path = self.root / '.veera-artifacts/amend.json'
        report_path.parent.mkdir()
        report_path.write_text(json.dumps(self.report))
        result = cli(self, 'amend', '--root', str(self.root), '--file', str(report_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        after = json.loads(result.stdout)
        for key in ('run_id', 'root', 'started_at', 'deadline', 'soft_deadline', 'baseline', 'repairs', 'usage', 'status', 'phase', 'repair_escalation', 'checkpoint'):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(before['events'], after['events'][:-1])
        self.assertEqual(after['checks'], {})
        self.assertIsNone(after['review'])
        self.assertEqual(after['amendments'][0]['prior_contract'], before['contract'])
        self.assertEqual(after['amendments'][0]['prior_contract_hash'], before['contract_hash'])
        self.assertEqual(after['amendments'][0]['report'], self.report)
        self.assertEqual(after['contract_hash'], d.digest(after['contract']))
        for key in ('scope', 'checks', 'criteria'):
            self.assertEqual(after['contract'][key], before['contract'][key] + self.report['add_' + key])
        self.assertEqual(owner_bytes, Path(self.capability).read_bytes())
        self.assertEqual(source, d.snapshot(self.root))
        resumed = d.resume(self.root, {'checkpoint_id': before['checkpoint']['id'], 'authorization': 'Fixture separate resume approval', 'reason': 'Ready', 'additional_minutes': 0})
        self.assertEqual(resumed['status'], 'active')
        self.assertEqual(resumed['deadline'], before['deadline'])
        self.assertEqual(resumed['amendments'], after['amendments'])

    def test_discovery_traceability_survives_public_additive_amendment(self):
        from test_discovery import example
        # Add a valid brief to this isolated stopped-task fixture.
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state['contract']['discovery'] = example()
            d.validate_contract(state['contract'], self.root)
            state['contract_hash'] = d.digest(state['contract'])
            d.save(directory, state)
        before = d.status(self.root)
        self.report['expected_contract_hash'] = before['contract_hash']
        self.assert_rejected(pattern='Discovery')
        self.report['add_discovery'] = {
            'evidence': [{'id': 'E3', 'kind': 'user-request', 'source': self.report['authorization'], 'finding': 'Include helper behavior'}],
            'requirements': [{'id': 'R2', 'text': 'Helper behavior', 'basis': 'user-request', 'evidence_ids': ['E3'], 'criteria': ['C2']}],
            'plan': [{'id': 'P2', 'action': 'Verify helper', 'requirement_ids': ['R2'], 'checks': ['helper']}]}
        report_path = self.root / '.veera-artifacts/amend-discovery.json'
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(json.dumps(self.report))
        result = cli(self, 'amend', '--root', str(self.root), '--file', str(report_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        after = json.loads(result.stdout)
        self.assertEqual(after['amendments'][-1]['prior_contract'], before['contract'])
        self.assertEqual(after['contract']['discovery']['requirements'][:1], example()['requirements'])
        self.assertEqual(after['status'], before['status'])
        self.assertEqual(after['deadline'], before['deadline'])
        self.assertEqual(len(after['contract']['discovery']['requirements']), 2)

    def test_wrong_owner_capability_root_fail_before_report_read(self):
        for session, capability, root in [('foreign', self.capability, self.root), (self.session_id, '/wrong', self.root), (self.session_id, self.capability, self.root.parent)]:
            with self.subTest(session=session, capability=capability, root=root), patch.object(self, 'session_id', session), patch.object(self, 'capability', capability), patch.object(d, 'read_json', side_effect=AssertionError('Unauthorized input read')):
                result = cli(self, 'amend', '--root', str(root), '--file', '/never/read')
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('error', result.stderr)

    def test_only_stopped_v2_tasks_can_amend(self):
        for status in ('active', 'ready', 'complete', 'verified-local', 'published'):
            with self.subTest(status=status), d.locked(self.root) as directory:
                state = d.load(directory)
                state['status'] = status
                d.save(directory, state)
            self.assert_rejected(pattern='stopped v2')
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state.update(status='user-stopped', version=1)
            d.save(directory, state)
        self.assert_rejected(pattern='stopped v2')

    def test_running_or_publication_attempt_is_immutable(self):
        for field in ('running', 'push_attempted'):
            with self.subTest(field=field), d.locked(self.root) as directory:
                state = copy.deepcopy(self.before)
                state[field] = True
                d.save(directory, state)
            self.assert_rejected(pattern='running|publication')

    def test_stale_identity_checkpoint_hash_and_source_rejected(self):
        for field in ('run_id', 'checkpoint_id', 'expected_contract_hash'):
            report = {**self.report, field: 'stale'}
            with self.subTest(field=field):
                self.assert_rejected(report)
        (self.root / 'helper.py').write_text('changed before amendment')
        self.assert_rejected(pattern='Checkpoint source changed')

    def test_missing_or_nontext_authorization_and_reason_rejected(self):
        for key in ('authorization', 'reason'):
            for value in (None, '', '  ', True, {}, []):
                with self.subTest(key=key, value=value):
                    self.assert_rejected({**self.report, key: value})
            report = dict(self.report)
            del report[key]
            self.assert_rejected(report)

    def test_unknown_fields_and_attempted_weakening_rejected(self):
        for key, value in [('contract', {}), ('scope', []), ('checks', []), ('criteria', []), ('max_repairs', 3), ('additional_minutes', 120), ('root', '/other'), ('owner', 'other'), ('delivery_mode', 'publish')]:
            with self.subTest(key=key):
                self.assert_rejected({**self.report, key: value})
        for key in ('criteria', 'checks'):
            replacement = copy.deepcopy(self.before['contract'][key][0])
            if key == 'checks':
                replacement.update(timeout_seconds=3600, count_pattern=r'(0)')
            else:
                replacement.update(text='Weaker acceptance', checks=['helper'])
            self.assert_rejected({**self.report, 'add_' + key: [replacement]})
        for key in ('add_checks', 'add_criteria'):
            report = copy.deepcopy(self.report)
            report[key][0]['unsupported'] = True
            self.assert_rejected(report)

    def test_invalid_or_protected_scope_and_ignored_inputs_rejected(self):
        for scope in ('../peer', '/outside', '.', './', 'src/../peer', 'src//file', 'C:/outside', r'src\file', '.git/config', '.veera/state.json', '.codex/config.toml', '.claude/settings.json', '.veera-artifacts/source.py', '*.py', 'src/.env', 'src/file:stream', 'src/./file'):
            with self.subTest(scope=scope):
                self.assert_rejected({**self.report, 'add_scope': [scope]})
        (self.root / '.gitignore').write_text('ignored.py\n')
        (self.root / 'ignored.py').write_text('ignored source')
        saved = d.checkpoint(self.root, 'Observe ignore configuration')
        report = {**self.report, 'checkpoint_id': saved['checkpoint']['id'], 'add_scope': ['ignored.py']}
        self.assert_rejected(report)

    def test_windows_invalid_characters_and_device_scope_rejected(self):
        for scope in ('bad|name.py', 'bad<name.py', 'bad>name.py', 'bad"name.py', 'CON', 'src/nul.py', 'src/AUX.txt', 'PRN/', 'src/COM1.log', 'src/lpt9.py', 'src/COM\u00b9.log', 'src/CONIN$', 'src/conout$.txt', 'src/CON .txt'):
            with self.subTest(scope=scope):
                self.assert_rejected({**self.report, 'add_scope': [scope]}, pattern='scope')

    def test_scope_rejects_junction_or_symlink_target_and_ancestor(self):
        protected = self.root / '.codex'
        protected.mkdir()
        alias = self.root / 'alias'
        if os.name == 'nt':
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(protected)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(alias.is_junction())
        else:
            alias.symlink_to(protected, target_is_directory=True)
        saved = d.checkpoint(self.root, 'Observe disposable alias')
        for scope in ('alias', 'alias/new.py'):
            with self.subTest(scope=scope):
                report = {**self.report, 'checkpoint_id': saved['checkpoint']['id'], 'add_scope': [scope]}
                self.assert_rejected(report, pattern='links|junctions')

    def test_stale_replay_fails_and_subsequent_amendment_appends_history(self):
        first = d.amend(self.root, self.report)
        self.assert_rejected(pattern='hash')
        second_report = {**self.report, 'expected_contract_hash': first['contract_hash'], 'add_scope': ['next.py'], 'add_criteria': [], 'add_checks': []}
        second = d.amend(self.root, second_report)
        self.assertEqual(second['amendments'][:-1], first['amendments'])
        self.assertEqual(second['amendments'][-1]['prior_contract'], first['contract'])

    def test_missing_checkpoint_and_empty_delta_rejected(self):
        self.assert_rejected({key: value for key, value in self.report.items() if not key.startswith('add_')})
        with d.locked(self.root) as directory:
            state = d.load(directory)
            del state['checkpoint']
            d.save(directory, state)
        self.assert_rejected(pattern='checkpoint')

    def test_amend_cannot_restore_exhausted_time_or_repairs(self):
        for reason in ('time', 'repairs'):
            with self.subTest(reason=reason), d.locked(self.root) as directory:
                state = copy.deepcopy(self.before)
                if reason == 'time':
                    state.update(status='budget-exhausted', deadline=1)
                else:
                    state.update(status='blocked', repairs=state['contract']['max_repairs'])
                d.save(directory, state)
            amended = d.amend(self.root, self.report)
            self.assertEqual(amended['deadline'], state['deadline'])
            self.assertEqual(amended['repairs'], state['repairs'])
            with self.assertRaisesRegex(d.DeliveryError, 'budget exhausted|Repair ceiling'):
                d.resume(self.root, {'checkpoint_id': state['checkpoint']['id'], 'authorization': 'Fixture resume consent', 'reason': 'Fixture', 'additional_minutes': 0})
            self.assertEqual(amended, d.status(self.root))

    def test_codex_exhausted_recovery_keeps_controller_budget_validation(self):
        import codex_hook
        self.enterContext(patch.dict(os.environ, {'VEERA_HOST': 'codex'}))
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state.update(status='budget-exhausted', deadline=1, repairs=1)
            d.save(directory, state)
        before = (self.root / '.veera/state.json').read_bytes()
        owner = Path(self.capability).read_bytes()
        report = {'checkpoint_id': state['checkpoint']['id'], 'authorization': 'Fixture user approval',
                  'reason': 'Resolved fixture', 'additional_minutes': 150,
                  'time_plan': [{'id': 'P1', 'criterion_id': 'C1', 'minutes': 60, 'reason': 'Remaining implementation'},
                                {'id': 'P2', 'criterion_id': 'C1', 'minutes': 90, 'reason': 'Verification and review'}]}
        artifacts = self.root / '.veera-artifacts'
        artifacts.mkdir(exist_ok=True)
        report_path = artifacts / 'resume.json'
        prefix = '& ' if os.name == 'nt' else ''
        command = (f'{prefix}"{Path(sys.executable)}" "{Path(d.__file__)}" resume '
                   f'--root "{self.root}" --session-id {self.session_id} '
                   f'--capability-file "{self.capability}" --file "{report_path}"')
        payload = {'hook_event_name': 'PreToolUse', 'session_id': self.session_id,
                   'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}}
        for delta in ({'additional_minutes': 0}, {'additional_minutes': 151},
                      {'authorization': ''}, {'checkpoint_id': 'stale'}, {'time_plan': []},
                      {'additional_minutes': True}, {'additional_minutes': float('nan')},
                      {'time_plan': [report['time_plan'][0], report['time_plan'][0]]},
                      {'time_plan': [{**report['time_plan'][0], 'criterion_id': 'foreign'}]},
                      {'time_plan': [{**report['time_plan'][0], 'minutes': -1}]},
                      {'time_plan': [{**report['time_plan'][0], 'minutes': float('inf')}]},
                      {'time_plan': [{**report['time_plan'][0], 'reason': ''}]}):
            with self.subTest(delta=delta):
                report_path.write_text(json.dumps({**report, **delta}))
                self.assertEqual(codex_hook.handle(payload), {})
                result = cli(self, 'resume', '--root', str(self.root), '--file', str(report_path))
                self.assertEqual(result.returncode, 2)
                self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)
        report_path.write_text(json.dumps(report))
        self.assertEqual(cli(self, 'resume', '--root', str(self.root), '--file', str(report_path)).returncode, 0)
        after = d.status(self.root)
        self.assertEqual(after['repairs'], state['repairs'])
        self.assertEqual(after['started_at'], state['started_at'])
        self.assertEqual(Path(self.capability).read_bytes(), owner)

    def test_amend_requires_host_approval_on_stopped_task(self):
        for args in ('--file approval.json', '--file=approval.json'):
            command = f'python3 "{Path(d.__file__)}" amend --root "{self.root}" --session-id {self.session_id} --capability-file "{self.capability}" {args}'
            payload = {'session_id': self.session_id, 'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}}
            self.assertTrue(safety.evaluate(payload).startswith('ASK:'))

    def test_codex_recorded_authorization_amends_and_resumes_without_extra_prompt(self):
        import codex_hook
        self.enterContext(patch.dict(os.environ, {'VEERA_HOST': 'codex'}))
        artifacts = self.root / '.veera-artifacts'
        artifacts.mkdir(exist_ok=True)
        amendment = artifacts / 'amend.json'
        amendment.write_text(json.dumps(self.report))
        resume = artifacts / 'resume.json'
        resume.write_text(json.dumps({'checkpoint_id': self.before['checkpoint']['id'],
                                     'authorization': self.report['authorization'],
                                     'reason': 'Covered by fixture upfront authorization', 'additional_minutes': 0}))
        for operation, report in (('amend', amendment), ('resume', resume)):
            command = f'"{Path(sys.executable).as_posix()}" "{Path(d.__file__).as_posix()}" {operation} --root "{self.root.as_posix()}" --session-id {self.session_id} --capability-file "{Path(self.capability).as_posix()}" --file "{report.as_posix()}"'
            payload = {'hook_event_name': 'PreToolUse', 'session_id': self.session_id, 'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}}
            self.assertEqual(codex_hook.handle(payload), {})
            result = cli(self, operation, '--root', str(self.root), '--file', str(report))
            self.assertEqual(result.returncode, 0, result.stderr)
        state = d.status(self.root)
        self.assertEqual(state['status'], 'active')
        self.assertEqual(state['repairs'], self.before['repairs'])
        self.assertEqual(state['deadline'], self.before['deadline'])


if __name__ == '__main__':
    unittest.main()
