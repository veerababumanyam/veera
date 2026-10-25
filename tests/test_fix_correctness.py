"""Fix correctness: whole-contract fixes and defective checks corrected, never stranded."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
import delivery as d
import git_delivery as g

GOOD = "from app import value; assert value == 2; print('Ran 1 test')"


class FixCorrectnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.original = self.base / 'app'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.original)], check=True)
        g.git(self.original, 'config', 'user.email', 'fixture@example.invalid')
        g.git(self.original, 'config', 'user.name', 'Fixture')
        (self.original / 'app.py').write_text('value = 1\n')
        (self.original / 'calls.py').write_text('from app import value\n')
        (self.original / 'tests').mkdir()
        (self.original / 'tests/test_app.py').write_text('pass\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-m', 'Fixture baseline')
        self.root = Path(g.workspace(self.original, 'fix')['root'])
        self.contract = {'delivery_mode': 'local-verify', 'lane': 'small', 'scope': ['app.py'],
                         'criteria': [{'id': 'C1', 'text': 'Value is corrected', 'checks': ['unit']}],
                         'checks': [self.spec("import sys; print('No module named pytest'); sys.exit(1)")]}

    def spec(self, code, **extra):
        return {'id': 'unit', 'kind': 'test', 'argv': [sys.executable, '-B', '-c', code], 'count_pattern': r'Ran (\d+) test', **extra}

    def start(self, contract=None):
        return d.init(self.root, 'fix', 'Correct value', contract or self.contract, 5, 10)

    def test_defective_check_is_corrected_and_the_run_finishes(self):
        self.start()
        (self.root / 'app.py').write_text('value = 2\n')
        failed = d.verify_local(self.root, notes='Value set to 2')
        self.assertEqual((failed['status'], failed['defective_check']), ('failed', 'No module named pytest'))
        self.assertIn('correct-contract', failed['next'])
        corrected = d.correct_contract(self.root, 'Container has no pytest; use the project runner', checks=[self.spec(GOOD)])
        self.assertEqual((corrected['status'], corrected['corrections_left']), ('active', d.SMALL_CORRECTIONS - 1))
        closed = d.verify_local(self.root, notes='Value set to 2; C1 by unit after the check correction')
        self.assertEqual((closed['status'], closed['repairs']), ('verified-local', 0))
        self.assertEqual(closed['corrections'][0]['checks'], ['unit'])
        state = d.status(self.root)
        self.assertIn('pytest', state['review']['corrections'][0]['reason'])
        self.assertEqual(state['corrections'][0]['prior_results']['unit']['status'], 'failed')
        self.assertEqual(state['corrections'][0]['prior_contract']['checks'][0]['argv'][-1], self.contract['checks'][0]['argv'][-1])
        self.assertEqual(d.digest(state['contract']), state['contract_hash'])

    def test_fix_widens_to_a_call_site_outside_the_frozen_scope(self):
        self.contract['checks'] = [self.spec(GOOD)]
        self.start()
        (self.root / 'app.py').write_text('value = 2\n')
        (self.root / 'calls.py').write_text('from app import value as fixed\n')
        with self.assertRaisesRegex(d.DeliveryError, 'Out-of-scope'):
            d.verify_local(self.root, notes='Call site changed too')
        result = d.correct_contract(self.root, 'calls.py re-exports the value the issue names', add_scope=['calls.py'])
        self.assertEqual(result['scope'], ['app.py', 'calls.py'])
        self.assertEqual(d.verify_local(self.root, notes='Both sites corrected; C1 by unit')['status'], 'verified-local')

    def test_correction_guards(self):
        self.start()
        cases = [({'checks': [self.spec(GOOD, id='other')]}, 'by its ID'),
                 ({'checks': [dict(self.spec(GOOD), kind='static')]}, 'keeps the check kind'),
                 ({'checks': [self.spec(GOOD), self.spec(GOOD)]}, 'once'),
                 ({'add_scope': ['.env']}, 'Protected'),
                 ({'add_scope': ['../outside.py']}, 'canonical'),
                 ({'add_scope': ['app.py']}, 'add scope or replace'),
                 ({'checks': [self.spec(GOOD, count_pattern='none')]}, 'count_pattern'),
                 ({'add_scope': ['f%d.py' % i for i in range(d.SMALL_SCOPE)]}, 'at most')]
        for change, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(d.DeliveryError, message):
                    d.correct_contract(self.root, 'Fixture evidence', **change)
        with self.assertRaisesRegex(d.DeliveryError, 'evidence'):
            d.correct_contract(self.root, ' ', add_scope=['calls.py'])
        self.assertNotIn('corrections', d.status(self.root))

    def test_passing_check_is_not_replaced_and_allowance_is_bounded(self):
        self.contract['checks'] = [self.spec(GOOD)]
        self.start()
        (self.root / 'app.py').write_text('value = 2\n')
        d.phase(self.root, 'plan'), d.phase(self.root, 'implement'), d.phase(self.root, 'verify')
        self.assertEqual(d.check(self.root, 'unit')['status'], 'passed')
        with self.assertRaisesRegex(d.DeliveryError, 'not defective'):
            d.correct_contract(self.root, 'Weaken a passing check', checks=[self.spec("print('Ran 1 test')")])
        d.correct_contract(self.root, 'First widening', add_scope=['calls.py'])
        d.correct_contract(self.root, 'Second widening', add_scope=['tests/test_app.py'])
        with self.assertRaisesRegex(d.DeliveryError, 'allowance spent'):
            d.correct_contract(self.root, 'Third widening', add_scope=['notes.py'])

    def test_standard_lane_and_stopped_runs_are_not_corrected_in_place(self):
        self.contract.pop('lane')
        self.start()
        with self.assertRaisesRegex(d.DeliveryError, 'small-lane'):
            d.correct_contract(self.root, 'Fixture evidence', add_scope=['calls.py'])
        other = FixCorrectnessTests('test_correction_guards')
        other.setUp()
        self.addCleanup(other.temp.cleanup)
        other.start()
        d.stop(other.root, 'Fixture stop')
        with self.assertRaisesRegex(d.DeliveryError, 'user-stopped'):
            d.correct_contract(other.root, 'Fixture evidence', add_scope=['calls.py'])

    def test_fix_failures_are_not_called_defective(self):
        self.contract['checks'] = [self.spec(GOOD)]
        self.start()
        (self.root / 'app.py').write_text('value = 3\n')
        failed = d.verify_local(self.root, notes='Wrong value')
        self.assertNotIn('defective_check', failed)
        self.assertTrue(failed['next'].startswith('repair'))
        samples = {"ERROR: file or directory not found: tests/test_x.py": 'ERROR: file or directory not found',
                   "/bin/sh: pytest: command not found": 'command not found',
                   "tests finished: 0 passed, in 0.01 seconds": 'finished: 0 passed',
                   "Error: No such container: box": 'No such container',
                   "Ran 12 tests in 0.1s\nFAILED (failures=1)": ''}
        for tail, expected in samples.items():
            with self.subTest(tail=tail):
                self.assertEqual(d.defective_check({'exit_code': 1, 'reason': ''}, tail), expected)
        self.assertIn('no tests', d.defective_check({'exit_code': 0, 'reason': '', 'test_count': 0}, ''))

    def test_workspace_refuses_a_missing_test_file_before_binding(self):
        contract = dict(self.contract, checks=[self.spec(GOOD)])
        contract['checks'][0]['argv'] = ['bash', '-lc', 'cd /work/{TASK_NAME} && python -m pytest -q tests/test_utils.py::test_one']
        with self.assertRaisesRegex(d.DeliveryError, 'tests/test_utils.py'):
            d.workspace_init(self.original, 'two', None, 'fix', 'Correct value', contract, 5, 10)
        self.assertFalse((self.base / 'app-veera-two').exists())
        accepted = ['cd /work/{TASK_NAME} && python -B -m pytest tests/test_app.py',
                    'cd /work/{TASK_NAME}/tests && python runtests.py test_app.py',
                    'python /work/{TASK_NAME}/tests/test_app.py',
                    'PYTHONPATH=/work/{TASK_NAME} python -m pytest /testbed/elsewhere/test_z.py']
        for command in accepted:
            with self.subTest(command=command):
                contract['checks'][0]['argv'] = ['bash', '-lc', command]
                self.assertEqual(d.check_paths(contract, self.original), [])
        contract['scope'] = ['app.py', 'tests/test_new.py']
        contract['checks'][0]['argv'] = ['bash', '-lc', 'cd /work/{TASK_NAME} && python -m pytest tests/test_new.py']
        self.assertEqual(d.check_paths(contract, self.original), [])

    def test_workspace_warns_when_pytest_meets_a_project_runner(self):
        (self.original / 'bin').mkdir()
        (self.original / 'bin/test').write_text('#!/usr/bin/env python\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-m', 'Own runner')
        contract = dict(self.contract, checks=[self.spec(GOOD)])
        contract['checks'][0]['argv'] = ['bash', '-lc', 'cd /work/{TASK_NAME} && python -m pytest tests/test_app.py']
        result = d.workspace_init(self.original, 'three', None, 'fix', 'Correct value', contract, 5, 10)
        self.assertIn('bin/test', result['check_warnings'][0])
        contract['checks'][0]['argv'] = ['bash', '-lc', 'cd /work/{TASK_NAME} && python bin/test tests/test_app.py']
        self.assertEqual(d.check_paths(contract, self.original), [])

    def test_cli_correct_contract(self):
        import ownership
        from session_fixture import cli
        self.enterContext(patch.object(ownership, 'REGISTRY', self.base / 'sessions'))
        self.session_id = 'fixture-correct-owner'
        metadata = d.read_json(self.root / '.veera/workspace.json')
        metadata['session_id'] = self.session_id
        d.atomic(self.root / '.veera/workspace.json', metadata)
        self.capability = ownership.enroll(self.session_id, self.root, metadata['id'])
        self.start()
        checks = self.base / 'checks.json'
        checks.write_text(json.dumps({'checks': [self.spec(GOOD + "; print('{TASK_NAME}')")]}))
        result = cli(self, 'correct-contract', '--root', str(self.root), '--reason', 'No module named pytest in the box',
                     '--add-scope', 'calls.py', '--file', str(checks))
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output['scope'], ['app.py', 'calls.py'])
        self.assertIn(self.root.name, output['argv']['unit'][-1])
        checks.write_text(json.dumps({'checks': [], 'criteria': []}))
        refused = cli(self, 'correct-contract', '--root', str(self.root), '--reason', 'Extra fields', '--file', str(checks))
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('only', refused.stderr)


class FixContractSkillTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / 'skills/fix/SKILL.md').read_text(encoding='utf-8')
        self.lane = re.search(r'^## Small-fix lane.*?(?=^## )', self.text, re.M | re.S).group(0)

    def test_lane_checks_every_case_the_issue_names(self):
        for phrase in ('Contract sweep', 'Re-read the issue', 'every case', 'call site', 'correct-contract --root TASK',
                       '--add-scope', 'NotImplementedError', 'xfail'):
            self.assertIn(phrase, self.lane)

    def test_defective_check_is_corrected_not_stopped(self):
        self.assertIn('defective check', self.lane)
        self.assertNotRegex(self.lane, r'defective check[^.]*call `stop')
        self.assertIn('bin/test', self.lane)
        self.assertIn('check_warnings', self.lane)

    def test_contracts_document_correction(self):
        for name in ('docs/agent-contract.md', 'docs/intake-and-autonomy.md', 'docs/requirements-analysis.md'):
            with self.subTest(doc=name):
                text = (ROOT / name).read_text(encoding='utf-8')
                self.assertTrue('correct-contract' in text or 'every case' in text)
        self.assertIn('correct-contract', (ROOT / 'docs/agent-contract.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
