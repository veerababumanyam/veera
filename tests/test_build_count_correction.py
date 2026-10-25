"""Build count correction: a clean suite whose summary line went unread is re-read, never stranded.

A standard-lane run whose frozen count_pattern was re-encoded (a shell turning a
non-ASCII marker into mojibake) used to fail with exit 0 and zero tests and then
stop for a human-approved recovery. Disposable repos only.
"""
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

SUITE = "import sys; sys.stdout.buffer.write('\\u2714 C1 holds\\n\\u2139 tests 3\\n\\u2139 pass 3\\n\\u2139 fail 0\\n'.encode())"
GARBLED = '(?m)^(?:#|â„¹) pass (\\d+)\\s*$'  # What a cp1252 round trip makes of the marker.
READABLE = '(?m)^(?:#|\\u2139) pass (\\d+)\\s*$'


class BuildCountCorrectionTests(unittest.TestCase):
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
        self.root = Path(g.workspace(self.original, 'build')['root'])
        self.contract = {'delivery_mode': 'local-verify', 'scope': ['app.py'],
                         'criteria': [{'id': 'C1', 'text': 'Value holds', 'checks': ['suite']}],
                         'checks': [self.spec(SUITE, GARBLED)]}

    def spec(self, code, pattern):
        return {'id': 'suite', 'kind': 'test', 'argv': [sys.executable, '-B', '-c', code], 'count_pattern': pattern}

    def verify(self, contract=None):
        d.init(self.root, 'build', 'Build value', contract or self.contract, 5, 10)
        for name in ('plan', 'implement', 'verify'):
            d.phase(self.root, name)
        return d.check(self.root, 'suite')

    def test_unread_summary_is_corrected_and_the_check_passes(self):
        failed = self.verify()
        self.assertEqual((failed['status'], failed['exit_code'], failed['test_count']), ('failed', 0, 0))
        self.assertTrue(d.unread_count(failed))
        before = d.status(self.root)
        result = d.correct_contract(self.root, 'Log prints the summary line; the frozen pattern is mojibake',
                                    checks=[{'id': 'suite', 'count_pattern': READABLE}])
        self.assertEqual((result['status'], result['corrections_left']), ('active', d.SMALL_CORRECTIONS - 1))
        passed = d.check(self.root, 'suite')
        self.assertEqual((passed['status'], passed['test_count']), ('passed', 3))
        state = d.status(self.root)
        self.assertEqual((state['repairs'], state['deadline']), (before['repairs'], before['deadline']))
        correction = state['corrections'][0]
        self.assertEqual((correction['recounted'], correction['prior_results']['suite']['test_count']), ({'suite': 3}, 0))
        self.assertEqual(state['contract']['checks'][0]['argv'], self.contract['checks'][0]['argv'])

    def test_corrections_that_could_weaken_the_check_are_refused(self):
        self.verify()
        before = (self.root / '.veera/state.json').read_bytes()
        refused = [({'add_scope': ['README.md']}, 'small-lane'),
                   ({'checks': [{'id': 'suite', 'count_pattern': r'(?m)^# pass (\d+)'}]}, 'count the tests'),
                   ({'checks': [{'id': 'suite', 'count_pattern': r'(\d+)'}]}, None),
                   ({'checks': [{'id': 'suite', 'count_pattern': r'(pass) (\d+)'}]}, 'one capture group'),
                   ({'checks': [{'id': 'suite', 'count_pattern': '(unclosed'}]}, 'Invalid count_pattern'),
                   ({'checks': [{**self.spec("print('pass 3')", READABLE)}]}, 'only count_pattern'),
                   ({'checks': [{'id': 'suite', 'kind': 'static', 'count_pattern': READABLE}]}, 'only count_pattern'),
                   ({'checks': [{'id': 'suite'}]}, 'only count_pattern')]
        for change, message in refused:
            if message is None:
                continue  # A pattern that counts digits anywhere is accepted only because the log proves tests ran.
            with self.subTest(change=change), self.assertRaisesRegex(d.DeliveryError, message):
                d.correct_contract(self.root, 'Fixture evidence', **change)
            self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)

    def test_failing_suites_and_unrun_checks_still_need_repair(self):
        failing = "import sys; print('# pass 2'); print('# fail 1'); sys.exit(1)"
        self.contract['checks'] = [self.spec(failing, GARBLED)]
        self.assertEqual(self.verify()['exit_code'], 1)
        with self.assertRaisesRegex(d.DeliveryError, 'needs repair'):
            d.correct_contract(self.root, 'Fixture evidence', checks=[{'id': 'suite', 'count_pattern': r'# pass (\d+)'}])
        other = BuildCountCorrectionTests('test_failing_suites_and_unrun_checks_still_need_repair')
        other.setUp()
        self.addCleanup(other.temp.cleanup)
        d.init(other.root, 'build', 'Build value', other.contract, 5, 10)
        with self.assertRaisesRegex(d.DeliveryError, 'exited 0'):
            d.correct_contract(other.root, 'Fixture evidence', checks=[{'id': 'suite', 'count_pattern': READABLE}])

    def test_passing_checks_stopped_runs_and_spent_allowance_are_refused(self):
        self.contract['checks'] = [self.spec(SUITE, READABLE)]
        self.assertEqual(self.verify()['status'], 'passed')
        with self.assertRaisesRegex(d.DeliveryError, 'passing check'):
            d.correct_contract(self.root, 'Fixture evidence', checks=[{'id': 'suite', 'count_pattern': READABLE}])
        other = BuildCountCorrectionTests('test_passing_checks_stopped_runs_and_spent_allowance_are_refused')
        other.setUp()
        self.addCleanup(other.temp.cleanup)
        other.verify()
        d.stop(other.root, 'Fixture stop')
        with self.assertRaisesRegex(d.DeliveryError, 'user-stopped'):
            d.correct_contract(other.root, 'Fixture evidence', checks=[{'id': 'suite', 'count_pattern': READABLE}])

    def test_correction_allowance_is_shared(self):
        self.verify()
        with patch.object(d, 'SMALL_CORRECTIONS', 0), self.assertRaisesRegex(d.DeliveryError, 'allowance spent'):
            d.correct_contract(self.root, 'Fixture evidence', checks=[{'id': 'suite', 'count_pattern': READABLE}])

    def test_cli_check_points_at_the_correction_and_the_hook_allows_it(self):
        import ownership
        import safety
        from session_fixture import cli
        self.enterContext(patch.object(ownership, 'REGISTRY', self.base / 'sessions'))
        self.session_id = 'fixture-count-owner'
        metadata = d.read_json(self.root / '.veera/workspace.json')
        metadata['session_id'] = self.session_id
        d.atomic(self.root / '.veera/workspace.json', metadata)
        self.capability = ownership.enroll(self.session_id, self.root, metadata['id'])
        d.init(self.root, 'build', 'Build value', self.contract, 5, 10)
        for name in ('plan', 'implement', 'verify'):
            d.phase(self.root, name)
        result = cli(self, 'check', '--root', str(self.root), '--id', 'suite')
        output = json.loads(result.stdout)
        self.assertEqual(output['defective_check'], d.COUNT_ONLY)
        self.assertIn('correct-contract --root TASK', output['next'])
        checks = self.base / 'checks.json'
        checks.write_text(json.dumps({'checks': [{'id': 'suite', 'count_pattern': READABLE}]}))
        command = (f'python3 {Path(d.__file__).resolve()} correct-contract --root {self.root} --session-id {self.session_id} '
                   f'--capability-file {self.capability} --reason Summary-line-unread --file {checks}')
        with patch.dict('os.environ', {'VEERA_HOST': 'claude'}):
            self.assertIsNone(safety.evaluate({'session_id': self.session_id, 'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}}))
        corrected = cli(self, 'correct-contract', '--root', str(self.root), '--reason', 'Summary line unread', '--file', str(checks))
        self.assertEqual(corrected.returncode, 0, corrected.stderr)
        self.assertEqual(json.loads(cli(self, 'check', '--root', str(self.root), '--id', 'suite').stdout)['status'], 'passed')


class BuildCountSkillTests(unittest.TestCase):
    def test_build_skill_routes_unread_counts_to_correction_and_keeps_contracts_ascii(self):
        text = (ROOT / 'skills/build/SKILL.md').read_text(encoding='utf-8')
        example = re.search(r'Example for a node:test suite: `(\{.*?\})`', text).group(1)
        self.assertTrue(example.isascii())
        self.assertIn('\\u2139', example)
        for phrase in ('`defective_check`', 'correct-contract --root TASK --reason EVIDENCE --file FILE', 'no other field of the check may change'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertIn('Standard lane: only a new `count_pattern`', (ROOT / 'docs/agent-contract.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
