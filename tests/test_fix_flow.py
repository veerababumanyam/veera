"""Small-lane Fix flow: proportionate ceremony with unchanged delivery gates."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import delivery as d
import git_delivery as g


class FixFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.original = self.base / 'app'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.original)], check=True)
        g.git(self.original, 'config', 'user.email', 'fixture@example.invalid')
        g.git(self.original, 'config', 'user.name', 'Fixture')
        (self.original / 'app.py').write_text('value = 1\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-m', 'Fixture baseline')
        self.initial = g.git(self.original, 'rev-parse', 'HEAD')
        self.root = Path(g.workspace(self.original, 'fix')['root'])
        self.contract = {'delivery_mode': 'local-verify', 'lane': 'small', 'scope': ['app.py'],
                         'criteria': [{'id': 'C1', 'text': 'Value is corrected', 'checks': ['unit']}],
                         'checks': [{'id': 'unit', 'kind': 'test', 'argv': [sys.executable, '-B', '-c', "from app import value; assert value == 2; print('Ran 1 test')"], 'count_pattern': r'Ran (\d+) test'}]}

    def start(self, minutes=5, hard_minutes=10):
        return d.init(self.root, 'fix', 'Correct value', self.contract, minutes, hard_minutes)

    def test_small_lane_closes_in_one_call(self):
        self.start()
        (self.root / 'app.py').write_text('value = 2\n')
        result = d.verify_local(self.root, notes='Diff sets value to 2; C1 covered by unit')
        self.assertEqual(result['status'], 'verified-local')
        self.assertEqual(result['checks']['unit']['test_count'], 1)
        self.assertIn('not independent', result['reviewer'])
        state = d.status(self.root)
        self.assertFalse(state['review']['independent'])
        self.assertEqual([e['detail'] for e in state['events'] if e['kind'] == 'phase'], ['plan', 'implement', 'verify', 'review'])
        self.assertEqual(g.git(self.root, 'rev-parse', 'HEAD'), self.initial)
        self.assertEqual((self.original / 'app.py').read_text(), 'value = 1\n')
        self.assertLess(len(json.dumps(result)), 2000)

    def test_failed_check_needs_repair_then_closes(self):
        self.start()
        (self.root / 'app.py').write_text('value = 3\n')
        result = d.verify_local(self.root, notes='First attempt')
        self.assertEqual((result['status'], result['failed_check']), ('failed', 'unit'))
        self.assertEqual(d.status(self.root)['status'], 'active')
        with self.assertRaisesRegex(d.DeliveryError, 'repair'):
            d.verify_local(self.root, notes='Unchanged retry')
        d.repair(self.root, 'Value 3 fails the frozen check; use 2')
        (self.root / 'app.py').write_text('value = 2\n')
        result = d.verify_local(self.root, notes='Value corrected after one repair')
        self.assertEqual((result['status'], result['repairs']), ('verified-local', 1))

    def test_out_of_scope_change_still_blocks(self):
        self.start()
        (self.root / 'app.py').write_text('value = 2\n')
        (self.root / 'other.py').write_text('x = 1\n')
        with self.assertRaisesRegex(d.DeliveryError, 'Out-of-scope'):
            d.verify_local(self.root, notes='Includes an unrelated file')

    def test_small_lane_is_bounded_and_unpublished(self):
        cases = [({'delivery_mode': 'publish', 'release': {'remote': 'origin'}}, 'local-verify only'),
                 ({'ui': True}, 'standard lane'),
                 ({'scope': ['f%d.py' % i for i in range(d.SMALL_SCOPE + 1)]}, 'at most'),
                 ({'lane': 'tiny'}, 'Unknown lane')]
        for change, message in cases:
            with self.subTest(message=message):
                contract = {**self.contract, **change}
                if 'release' in change:
                    contract.pop('delivery_mode')
                with self.assertRaisesRegex(d.DeliveryError, message):
                    d.validate_contract(contract, self.root)

    def test_standard_lane_still_needs_independent_review(self):
        self.contract.pop('lane')
        self.start()
        (self.root / 'app.py').write_text('value = 2\n')
        with self.assertRaisesRegex(d.DeliveryError, 'independent review'):
            d.verify_local(self.root, notes='Self-review is not enough here')
        report = {'reviewer': 'fixture-independent', 'fingerprint': d.digest(d.snapshot(self.root)), 'approved': True, 'criteria': ['C1'], 'notes': 'Fixture attestation'}
        self.assertEqual(d.verify_local(self.root, report=report)['status'], 'verified-local')

    def test_small_lane_soft_target_needs_no_committee(self):
        self.start(minutes=.0001, hard_minutes=10)
        time.sleep(.05)
        (self.root / 'app.py').write_text('value = 2\n')
        self.assertEqual(d.verify_local(self.root, notes='Finished after the soft target')['status'], 'verified-local')
        kinds = [e['kind'] for e in d.status(self.root)['events']]
        self.assertIn('soft-target', kinds)
        self.assertNotIn('replan', kinds)

    def test_standard_lane_soft_target_still_replans(self):
        self.contract.pop('lane')
        self.start(minutes=.0001, hard_minutes=10)
        time.sleep(.05)
        self.assertTrue(d.status(self.root)['replan_required'])

    def test_coordinator_decision_only_on_small_lane(self):
        self.start()
        decision = {'owner': 'coordinator', 'decision': 'Keep the same fix', 'reason': 'Bounded defect'}
        self.assertFalse(d.decision(self.root, decision)['replan_required'])
        other = FixFlowTests('test_small_lane_closes_in_one_call')
        other.setUp()
        self.addCleanup(other.temp.cleanup)
        other.contract.pop('lane')
        other.start()
        with self.assertRaisesRegex(d.DeliveryError, 'PM ownership'):
            d.decision(other.root, decision)

    def test_cli_verify_local_releases_binding(self):
        import ownership
        from session_fixture import cli
        self.enterContext(patch.object(ownership, 'REGISTRY', self.base / 'sessions'))
        self.session_id = 'fixture-small-owner'
        metadata = d.read_json(self.root / '.veera/workspace.json')
        metadata['session_id'] = self.session_id
        d.atomic(self.root / '.veera/workspace.json', metadata)
        self.capability = ownership.enroll(self.session_id, self.root, metadata['id'])
        self.start()
        (self.root / 'app.py').write_text('value = 2\n')
        result = cli(self, 'verify-local', '--root', str(self.root), '--notes', 'Diff sets value to 2')
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual((output['status'], output['session_binding']), ('verified-local', 'released'))
        self.assertIsNone(ownership.lookup(self.session_id))

    def placed_contract(self):
        contract = json.loads(json.dumps(self.contract))
        contract['checks'][0]['argv'][-1] = "import sys; print('{TASK_NAME}', sys.argv[1]); " + contract['checks'][0]['argv'][-1]
        contract['checks'][0]['argv'].append('{TASK}')
        return contract

    def test_workspace_init_binds_and_freezes_in_one_call(self):
        result = d.workspace_init(self.original, 'one', None, 'fix', 'Correct value', self.placed_contract(), 5, 10)
        task = Path(result['root'])
        self.assertNotIn('init_error', result)
        self.assertEqual((result['lane'], result['phase'], result['checks']), ('small', 'discover', ['unit']))
        frozen = d.read_json(task / '.veera-artifacts/contract.json')
        self.assertIn("print('" + task.name + "'", frozen['checks'][0]['argv'][-2])
        self.assertEqual(frozen['checks'][0]['argv'][-1], str(task))
        self.assertNotIn('{TASK', json.dumps(d.status(task)['contract']))
        (task / 'app.py').write_text('value = 2\n')
        self.assertEqual(d.verify_local(task, notes='Value set to 2; C1 by unit')['status'], 'verified-local')
        self.assertEqual(d.status(task)['checks']['unit']['argv'][-1], str(task))
        self.assertEqual((self.original / 'app.py').read_text(), 'value = 1\n')

    def test_workspace_init_refuses_before_binding(self):
        cases = [({'lane': 'standard'}, 'small-lane contracts only'),
                 ({'scope': ['../outside.py']}, 'repository-relative'),
                 ({'checks': [{'id': 'unit', 'kind': 'test', 'argv': ['python'], 'count_pattern': 'no group'}]}, 'count_pattern')]
        for change, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(d.DeliveryError, message):
                    d.workspace_init(self.original, 'two', None, 'fix', 'Correct value', {**self.contract, **change}, 5, 10)
                self.assertFalse((self.base / 'app-veera-two').exists())
        with self.assertRaisesRegex(d.DeliveryError, 'minutes'):
            d.workspace_init(self.original, 'two', None, 'fix', 'Correct value', self.contract, 20, 10)

    def test_workspace_init_failure_keeps_binding_and_names_next_step(self):
        with patch.object(d, 'init', side_effect=d.DeliveryError('fixture init refusal')):
            result = d.workspace_init(self.original, 'three', None, 'fix', 'Correct value', self.contract, 5, 10)
        self.assertEqual(result['init_error'], 'fixture init refusal')
        self.assertIn('contract.json', result['next'])
        self.assertTrue(Path(result['root']).is_dir())

    def test_cli_workspace_init_and_verify_local(self):
        import contextlib
        import io
        import ownership
        self.enterContext(patch.object(ownership, 'REGISTRY', self.base / 'sessions'))
        contract_file = self.base / 'contract.json'
        contract_file.write_text(json.dumps(self.placed_contract()))
        argv = ['delivery', 'workspace', '--root', str(self.original), '--task', 'cli', '--session-id', 'fixture-cli-owner',
                '--contract', str(contract_file), '--request', 'Correct value', '--minutes', '5', '--hard-minutes', '10']
        output = io.StringIO()
        with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(output):
            d.main()
        result = json.loads(output.getvalue())
        self.assertEqual(result['run_id'], d.status(result['root'])['run_id'])
        self.assertIsNotNone(ownership.lookup('fixture-cli-owner'))
        self.session_id, self.capability = 'fixture-cli-owner', result['capability_file']
        from session_fixture import cli
        (Path(result['root']) / 'app.py').write_text('value = 2\n')
        closed = cli(self, 'verify-local', '--root', result['root'], '--notes', 'Value set to 2')
        self.assertEqual(closed.returncode, 0, closed.stderr)
        self.assertEqual(json.loads(closed.stdout)['session_binding'], 'released')
        with patch.object(sys, 'argv', argv[:6] + ['--session-id', 'x', '--minutes', '5']), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                d.main()

    def test_failed_verify_local_carries_log_tail(self):
        self.start()
        (self.root / 'app.py').write_text('value = 3\n')
        result = d.verify_local(self.root, notes='Wrong value')
        self.assertIn('AssertionError', result['checks']['unit']['log_tail'])
        self.assertEqual(d.log_tail(self.root, '../state.json'), '')


class FixSkillTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / 'skills/fix/SKILL.md').read_text(encoding='utf-8')
        match = re.search(r'^## Small-fix lane.*?(?=^## )', self.text, re.M | re.S)
        self.assertIsNotNone(match)
        self.lane = match.group(0)

    def test_small_lane_is_self_contained(self):
        self.assertNotIn('${CLAUDE_PLUGIN_ROOT}/docs', self.lane)
        for phrase in ('verify-local', '"lane": "small"', 'fail', 'unattended', 'workspace', 'repair'):
            self.assertIn(phrase, self.lane.lower() if phrase == 'unattended' else self.lane)
        for skipped in ('dashboard', 'interview', 'consultation', 'review'):
            self.assertIn(skipped, self.lane.lower())

    def test_small_lane_preserves_safety(self):
        lower = self.lane.lower()
        for phrase in ('never push', 'shared repository state', 'task worktree'):
            self.assertIn(phrase, lower)

    def test_small_lane_example_contract_is_valid(self):
        line = next(l.strip().strip('`') for l in self.lane.splitlines() if l.strip().startswith('`{"delivery_mode"'))
        contract = json.loads(line)
        self.assertEqual(contract['lane'], 'small')
        argv = ' '.join(contract['checks'][0]['argv'])
        self.assertIn('PYTHONPATH=/work/{TASK_NAME}', argv)
        self.assertEqual(re.findall(contract['checks'][0]['count_pattern'], '3 passed in 1s'), ['3'])

    def test_small_lane_caps_overhead_and_keeps_contracts(self):
        for phrase in ('--contract FILE', 'about 20 tool calls', 'cd "TASK" && ', 'Do not commit', 'log_tail',
                       'return type and shape', 'defective check', 'No changelog'):
            self.assertIn(phrase, self.lane)

    def test_skill_stays_compact(self):
        self.assertLessEqual(len(self.text.splitlines()), 100)
        self.assertLess(len(self.text), 15000)

    def test_contracts_document_lane(self):
        for name in ('docs/agent-contract.md', 'docs/intake-and-autonomy.md', 'docs/requirements-analysis.md', 'docs/dashboard.md'):
            with self.subTest(doc=name):
                self.assertIn('small lane', (ROOT / name).read_text(encoding='utf-8').lower())


if __name__ == '__main__':
    unittest.main()
