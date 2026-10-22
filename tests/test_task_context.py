import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d
import task_context as c


class TaskContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / 'app.py').write_text('value = 1\n')
        (self.root / '.gitignore').write_text('.veera-artifacts/\n')
        (self.root / '.veera-artifacts').mkdir()
        (self.root / '.veera-artifacts/evidence.txt').write_text('Observed actual fixture result')
        self.contract = {'scope': ['app.py'], 'max_repairs': 3, 'criteria': [{'id': 'C1', 'text': 'Relevant behavior', 'checks': ['unit']}], 'checks': [{'id': 'unit', 'kind': 'test', 'argv': [sys.executable, '-c', "print('Ran 1 test')"], 'count_pattern': r'Ran (\d+) test'}]}
        self.state = d.init(self.root, 'fix', 'Fix task', self.contract, 1)

    def refs(self, name='.veera-artifacts/evidence.txt'):
        return [{'path': name, 'sha256': hashlib.sha256((self.root / name).read_bytes()).hexdigest()}]

    def proposal(self):
        brief = c.context(self.root)
        return {'run_id': brief['run_id'], 'contract_hash': brief['contract_hash'], 'expected_revision': brief['revision'], 'expected_fingerprint': brief['fingerprint'], 'proposal_id': 'P1', 'steward': 'fixture-steward', 'items': [{'id': 'fact1', 'summary': 'Relevant finding', 'text': 'Observed evidence supports this fact', 'kind': 'fact', 'sources': self.refs()}]}

    def op(self, **kwargs):
        return {'run_id': self.state['run_id'], **kwargs}

    def open(self, family='test', target='unit'):
        return c.blocker(self.root, self.op(op='open', family=family, target=target, criteria=['C1'], evidence=self.refs()))

    def exhaust(self, record):
        for n in range(record['limit']):
            attempt = c.blocker(self.root, self.op(op='attempt', id=record['id'], action='investigate ' + str(n), hypothesis='Distinct evidence-based route ' + str(n), evidence=self.refs()))
            record = c.blocker(self.root, self.op(op='result', id=record['id'], attempt_id=attempt['attempts'][-1]['id'], outcome='failed', evidence=self.refs()))
        return record

    def verify(self):
        for phase in ('plan', 'implement', 'verify'):
            d.phase(self.root, phase)
        d.check(self.root, 'unit')

    def test_import_replay_cas_and_source_freshness(self):
        proposal = self.proposal()
        receipt = c.import_context(self.root, proposal)
        self.assertEqual(receipt['revision'], 1)
        self.assertEqual(c.import_context(self.root, proposal), receipt)
        stale = copy.deepcopy(proposal)
        stale['proposal_id'] = 'P2'
        with self.assertRaises(d.DeliveryError):
            c.import_context(self.root, stale)
        proposal['items'][0]['text'] = 'conflicting replay'
        with self.assertRaises(d.DeliveryError):
            c.import_context(self.root, proposal)
        (self.root / '.veera-artifacts/evidence.txt').write_text('changed')
        self.assertFalse(c.context(self.root)['index'][0]['fresh'])

    def test_foreign_task_rejected_without_state_changes(self):
        proposal = self.proposal()
        proposal['run_id'] = 'another-task'
        with self.assertRaises(d.DeliveryError):
            c.import_context(self.root, proposal)
        self.assertEqual(c.context(self.root)['revision'], 0)

    def test_invalid_batch_atomicity(self):
        proposal = self.proposal()
        bad = copy.deepcopy(proposal['items'][0])
        bad['id'] = 'bad'
        bad['sources'][0]['sha256'] = 'stale'
        proposal['items'].append(bad)
        with self.assertRaises(d.DeliveryError):
            c.import_context(self.root, proposal)
        self.assertEqual(c.context(self.root)['index'], [])

    def test_source_path_and_secret_rejection(self):
        proposal = self.proposal()
        proposal['items'][0]['sources'] = [{'path': '../escape', 'sha256': 'x'}]
        with self.assertRaises(d.DeliveryError):
            c.import_context(self.root, proposal)
        proposal = self.proposal()
        proposal['items'][0]['text'] = '-----BEGIN RSA PRIVATE KEY-----'
        with self.assertRaises(d.DeliveryError):
            c.import_context(self.root, proposal)

    def test_duplicate_blocker_preserves_three_attempt_ceiling(self):
        record = self.exhaust(self.open())
        duplicate = self.open(target=' UNIT ')
        self.assertEqual(record['id'], duplicate['id'])
        self.assertEqual(len(duplicate['attempts']), 3)
        self.assertEqual(duplicate['status'], 'escalated')
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='attempt', id=record['id'], action='fourth', hypothesis='another', evidence=self.refs()))
        self.assertEqual(d.status(self.root)['status'], 'active')

    def test_pending_attempt_cannot_reset_by_reopen(self):
        record = self.open()
        pending = c.blocker(self.root, self.op(op='attempt', id=record['id'], action='inspect', hypothesis='cause', evidence=self.refs()))
        self.open()
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='attempt', id=record['id'], action='again', hypothesis='changed', evidence=self.refs()))
        result = c.blocker(self.root, self.op(op='result', id=record['id'], attempt_id=pending['attempts'][-1]['id'], outcome='failed', evidence=self.refs()))
        self.assertEqual(result['status'], 'open')

    def test_permission_denial_zero_retries(self):
        record = self.open(family='permission')
        self.assertEqual(record['status'], 'human-required')
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='attempt', id=record['id'], action='retry', hypothesis='retry', evidence=self.refs()))
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='resolve', id=record['id'], evidence=self.refs()))

    def test_human_resolution_requires_attestation_and_fresh_gates(self):
        record = self.open(family='permission')
        report = self.op(id=record['id'], authorization='Actual user approval fixture', evidence=self.refs())
        resolved = c.human_resolve(self.root, report)
        self.assertEqual(resolved['status'], 'resolved')
        self.assertEqual(d.status(self.root)['checks'], {})
        import safety
        from session_fixture import bind
        session_id, capability = bind(self, self.root)
        command = f'python3 {Path(d.__file__)} blocker-human-resolve --root {self.root} --file approval.json'
        response = safety.evaluate({'session_id': session_id, 'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}})
        self.assertTrue(response.startswith('ASK:'))

    def test_single_alternative_does_not_reset_counters(self):
        record = self.exhaust(self.open())
        op = self.op(op='decision', id=record['id'], owner='pm', consulted=['advisor', 'architect'], choice='alternative', plan='Independent in-scope route, not a fourth retry', evidence=self.refs())
        c.blocker(self.root, op)
        self.assertEqual(len(d.status(self.root)['blockers'][record['id']]['attempts']), 3)
        another = self.exhaust(self.open(target='other'))
        op['id'] = another['id']
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, op)

    def test_resolution_requires_relevant_fresh_checks(self):
        record = self.open()
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='resolve', id=record['id'], evidence=self.refs()))
        self.verify()
        resolved = c.blocker(self.root, self.op(op='resolve', id=record['id'], evidence=self.refs()))
        self.assertEqual(resolved['status'], 'resolved')
        d.phase(self.root, 'review')
        d.review(self.root, {'reviewer': 'fixture', 'fingerprint': d.digest(d.snapshot(self.root)), 'approved': True, 'criteria': ['C1'], 'notes': 'Fixture'})
        self.assertEqual(d.finish(self.root)['status'], 'complete')

    def test_unresolved_blocker_prevents_finish(self):
        self.open()
        self.verify()
        d.phase(self.root, 'review')
        d.review(self.root, {'reviewer': 'fixture', 'fingerprint': d.digest(d.snapshot(self.root)), 'approved': True, 'criteria': ['C1'], 'notes': 'Fixture'})
        with self.assertRaises(d.DeliveryError):
            d.finish(self.root)

    def test_escalated_human_decision_cannot_use_agent_resolve(self):
        record = self.exhaust(self.open())
        c.blocker(self.root, self.op(op='decision', id=record['id'], owner='pm', consulted=['advisor', 'architect'], choice='human-required', plan='Product decision needs user', evidence=self.refs()))
        self.verify()
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='resolve', id=record['id'], evidence=self.refs()))

    def test_ambiguous_attempt_requires_observed_state_reconciliation(self):
        record = self.open()
        pending = c.blocker(self.root, self.op(op='attempt', id=record['id'], action='inspect', hypothesis='cause', evidence=self.refs()))
        identity = pending['attempts'][-1]['id']
        c.blocker(self.root, self.op(op='result', id=record['id'], attempt_id=identity, outcome='ambiguous', evidence=self.refs()))
        self.open()  # Duplicate report must not erase the reconciliation barrier.
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='attempt', id=record['id'], action='different', hypothesis='next', evidence=self.refs()))
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='reconcile', id=record['id'], attempt_id=identity, outcome='failed', evidence=self.refs()))
        (self.root / '.veera-artifacts/observed.txt').write_text('Checked actual state after timeout')
        reconciled = c.blocker(self.root, self.op(op='reconcile', id=record['id'], attempt_id=identity, outcome='failed', evidence=self.refs('.veera-artifacts/observed.txt')))
        self.assertEqual(reconciled['status'], 'open')
        self.assertEqual(len(reconciled['attempts']), 1)

    def test_zero_local_allowance_escalates_immediately(self):
        # Test a stricter valid frozen contract in a separate fixture run.
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state['contract']['max_repairs'] = 0
            state['contract_hash'] = d.digest(state['contract'])
            d.save(directory, state)
        record = self.open()
        self.assertEqual(record['status'], 'escalated')
        c.blocker(self.root, self.op(op='decision', id=record['id'], owner='pm', consulted=['advisor', 'architect'], choice='prioritize-independent', plan='Investigate unrelated eligible work', evidence=self.refs()))
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='attempt', id=record['id'], action='repair', hypothesis='try', evidence=self.refs()))

    def test_global_exhaustion_prevents_new_corrective_attempt(self):
        record = self.open()
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state['repairs'] = 3
            d.save(directory, state)
        with self.assertRaises(d.DeliveryError):
            c.blocker(self.root, self.op(op='attempt', id=record['id'], action='repair', hypothesis='try', evidence=self.refs()))
        saved = d.status(self.root)['blockers'][record['id']]
        self.assertEqual(saved['status'], 'escalated')
        self.assertEqual(saved['attempts'], [])

    def test_exhaustion_preserves_all_protected_blocker_states(self):
        self.verify()
        for status in ('human-required', 'attempting', 'reconciliation-required'):
            with self.subTest(status=status):
                record = self.open(target=status)
                with d.locked(self.root) as directory:
                    state = d.load(directory)
                    state['blockers'][record['id']]['status'] = status
                    state['repairs'] = 3
                    d.save(directory, state)
                before = copy.deepcopy(d.status(self.root)['blockers'][record['id']])
                with self.assertRaises(d.DeliveryError):
                    c.blocker(self.root, self.op(op='attempt', id=record['id'], action='retry', hypothesis='must not run', evidence=self.refs()))
                after = d.status(self.root)['blockers'][record['id']]
                self.assertEqual(before, after)
                with self.assertRaises(d.DeliveryError):
                    c.blocker(self.root, self.op(op='resolve', id=record['id'], evidence=self.refs()))

    def test_read_context_does_not_mutate_memory_revision(self):
        c.import_context(self.root, self.proposal())
        first = c.context(self.root)
        second = c.context(self.root)
        self.assertEqual(first['revision'], second['revision'])
        self.assertNotIn('text', first['index'][0])
        self.assertIn('text', c.item(self.root, 'fact1'))


if __name__ == '__main__':
    unittest.main()
