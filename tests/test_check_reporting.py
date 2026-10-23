"""A counting correction cannot replace verification or promote old failures."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import test_amend as fixtures
import delivery as d
import check_reporting as reporting
import git_delivery as g
from session_fixture import cli


class ReportingTests(unittest.TestCase):
    def setUp(self):
        fixtures.AmendmentTests.setUp(self)
        self.evidence = self.root / '.veera-artifacts'
        self.evidence.mkdir()
        self.manifest = {'campaign_id': 'fixture-live', 'engines': ['owned', 'upstream'],
                         'concurrencies': [1, 4, 16], 'repetitions': 3}
        self.results = {'campaign_id': 'fixture-live', 'live': True, 'runs': [
            {'engine': e, 'concurrency': c, 'repetition': r}
            for e in self.manifest['engines'] for c in self.manifest['concurrencies'] for r in range(3)]}
        self.write_json('manifest', self.manifest)
        self.write_json('results', self.results)
        # This verifier has controllable fixture outcomes, no external services.
        (self.root / 'verify.py').write_text("""from pathlib import Path
import sys
base = Path('.veera-artifacts')
if (base / 'mutate').exists():
    (base / 'results.json').write_text('{}')
if (base / 'oversized').exists():
    print('x' * (9 * 1024 * 1024))
print('Matrix verified; no stdout test count')
sys.exit(1 if (base / 'fail').exists() else 0)
""")
        state = d.load(self.root / '.veera')
        self.spec = {'id': 'matrix', 'kind': 'test', 'argv': [sys.executable, '-B', 'verify.py', 'verify',
                     '--manifest', '.veera-artifacts/manifest.json', '--results', '.veera-artifacts/results.json'],
                     'count_pattern': r'Validated (\d+) cases', 'timeout_seconds': 5}
        state['contract'].update(scope=['app.py', 'verify.py'], checks=[self.spec],
                                 criteria=[{'id': 'C1', 'text': 'Original acceptance', 'checks': ['matrix']}])
        state['contract_hash'] = d.digest(state['contract'])
        state.update(status='active', phase='verify', baseline=d.snapshot(self.root), checks={})
        d.save(self.root / '.veera', state)
        self.failure = d.check(self.root, 'matrix')
        self.assertEqual((self.failure['status'], self.failure['exit_code'], self.failure['test_count']), ('failed', 0, 0))
        d.repair(self.root, 'Explicit counted reporting repair')
        d.stop(self.root, 'Review reporting correction')
        self.before = d.checkpoint(self.root, 'Preserve failed reporting evidence')
        self.adapter = {'kind': 'verified-json-matrix', **{key: self.pin(path) for key, path in (
            ('verifier', 'verify.py'), ('manifest', '.veera-artifacts/manifest.json'), ('results', '.veera-artifacts/results.json'))}}
        self.correction = {'run_id': self.before['run_id'], 'checkpoint_id': self.before['checkpoint']['id'],
            'expected_contract_hash': self.before['contract_hash'], 'check_id': 'matrix',
            'expected_check_hash': d.digest(self.spec), 'expected_result_hash': d.digest(self.failure),
            'log_sha256': hashlib.sha256((self.root / '.veera' / self.failure['log']).read_bytes()).hexdigest(),
            'authorization_id': 'fixture-human-reporting-17', 'authorization': 'Actual fixture approval',
            'reason': 'Original frozen verifier emits no count', 'adapter': self.adapter,
            'review': {'reviewer': 'separate-fixture-reviewer', 'notes': 'Reviewed unchanged verifier matrix equivalence',
                'approved': True, 'fingerprint': self.before['checkpoint']['fingerprint'],
                'check_hash': d.digest(self.spec), 'adapter_hash': d.digest(self.adapter)}}

    def write_json(self, name, value):
        (self.evidence / (name + '.json')).write_text(json.dumps(value))

    def pin(self, path):
        return {'path': path, 'sha256': hashlib.sha256((self.root / path).read_bytes()).hexdigest()}

    def resume(self):
        d.resume(self.root, {'checkpoint_id': self.before['checkpoint']['id'], 'authorization': 'Fixture continue',
                           'reason': 'Correction reviewed', 'additional_minutes': 0})
        d.phase(self.root, 'verify')

    def test_public_correction_preserves_history_budget_and_requires_fresh_check_and_review(self):
        owner = Path(self.capability).read_bytes()
        path = self.evidence / 'correction.json'
        path.write_text(json.dumps(self.correction))
        result = cli(self, 'correct-check-reporting', '--root', str(self.root), '--file', str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        after = d.load(self.root / '.veera')
        for key in ('contract', 'contract_hash', 'repairs', 'deadline', 'soft_deadline', 'started_at', 'status', 'checkpoint'):
            self.assertEqual(after[key], self.before[key], key)
        receipt = after['reporting_corrections'][0]
        self.assertEqual(receipt['prior_result'], self.failure)
        self.assertEqual(receipt['prior_check'], self.spec)
        self.assertEqual(after['events'][:-1], self.before['events'])
        self.assertEqual(after['checks'], {})
        self.assertIsNone(after['review'])
        self.assertEqual(Path(self.capability).read_bytes(), owner)
        self.resume()
        fresh = d.check(self.root, 'matrix')
        self.assertEqual((fresh['status'], fresh['test_count'], fresh['count_source']), ('passed', 18, 'verified-json-matrix'))
        self.assertNotEqual(fresh['log'], self.failure['log'])
        self.assertEqual(fresh['argv'], self.spec['argv'])
        self.assertNotIn('18', (self.root / '.veera' / fresh['log']).read_text())
        d.phase(self.root, 'review')
        with self.assertRaisesRegex(d.DeliveryError, 'independent review'):
            d.finish(self.root)
        state = d.load(self.root / '.veera')
        d.review(self.root, {'reviewer': 'final-fixture-reviewer', 'notes': 'All frozen criteria met', 'approved': True,
                            'criteria': ['C1'], 'fingerprint': fresh['fingerprint']})
        # Ignored artifacts changing invalidates both local finish and publish.
        self.write_json('results', {})
        for verify in (lambda: d.finish(self.root), lambda: g.validate_evidence(self.root, d.load(self.root / '.veera'))):
            with self.assertRaisesRegex(ValueError, 'Pinned evidence changed'):
                verify()
        self.write_json('results', self.results)
        d.decision(self.root, {'owner': 'pm', 'consulted': ['advisor', 'architect'],
                              'decision': 'Continue original acceptance', 'reason': 'Reporting equivalence reviewed'})
        self.assertEqual(d.finish(self.root)['status'], 'verified-local')

    def test_matrix_is_derived_and_rejects_missing_duplicate_extra_or_invalid_rows(self):
        variants = [self.results['runs'][:-1], self.results['runs'] + [self.results['runs'][0]],
                    [self.results['runs'][0]] * 18,
                    [{**row, 'repetition': 99} for row in self.results['runs']],
                    [{**row, 'concurrency': True} for row in self.results['runs']]]
        for rows in variants:
            self.write_json('results', {**self.results, 'runs': rows})
            adapter = {**self.adapter, 'results': self.pin('.veera-artifacts/results.json')}
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                reporting.validate(self.root, self.spec, adapter)
        self.write_json('results', self.results)
        for delta in ({'repetitions': 0}, {'repetitions': True}, {'engines': []}, {'concurrencies': [1, 1]}, {'campaign_id': 'foreign'}):
            self.write_json('manifest', {**self.manifest, **delta})
            adapter = {**self.adapter, 'manifest': self.pin('.veera-artifacts/manifest.json')}
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                reporting.validate(self.root, self.spec, adapter)
        self.write_json('manifest', {**self.manifest, 'repetitions': 1})
        self.write_json('results', {**self.results, 'runs': [r for r in self.results['runs'] if r['repetition'] == 0]})
        adapter = {**self.adapter, **{k: self.pin('.veera-artifacts/' + k + '.json') for k in ('manifest', 'results')}}
        self.assertEqual(reporting.validate(self.root, self.spec, adapter)['count'], 6)

    def test_invalid_authority_stale_bindings_and_failure_types_write_nothing(self):
        deltas = [{'authorization': ''}, {'authorization_id': ''}, {'run_id': 'other'}, {'checkpoint_id': 'old'},
                  {'expected_contract_hash': 'old'}, {'expected_check_hash': 'old'}, {'expected_result_hash': 'old'},
                  {'log_sha256': 'old'}, {'argv': ['fake']}, {'kind': 'static'}, {'criteria': []},
                  {'review': {**self.correction['review'], 'approved': False}},
                  {'review': {**self.correction['review'], 'adapter_hash': 'old'}}]
        for delta in deltas:
            before = (self.root / '.veera/state.json').read_bytes()
            with self.subTest(delta=delta), self.assertRaises((ValueError, d.DeliveryError)):
                d.correct_check_reporting(self.root, {**self.correction, **delta})
            self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)
        for delta in ({'exit_code': 1}, {'reason': 'output-capture-incomplete'}, {'test_count': 1},
                      {'fingerprint': 'old'}, {'repair_attempt': 1}):
            state = copy.deepcopy(self.before)
            failed = {**self.failure, **delta}
            state['checks']['matrix'] = failed
            d.save(self.root / '.veera', state)
            before = (self.root / '.veera/state.json').read_bytes()
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                d.correct_check_reporting(self.root, {**self.correction, 'expected_result_hash': d.digest(failed)})
            self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)

    def test_foreign_owner_denied_before_report_read(self):
        for command in ('correct-check-reporting', 'extend-repairs'):
            for session, capability, root in [('foreign', self.capability, self.root),
                    (self.session_id, '/wrong', self.root), (self.session_id, self.capability, self.root.parent)]:
                with self.subTest(command=command, session=session), patch.object(self, 'session_id', session), \
                     patch.object(self, 'capability', capability), patch.object(d, 'read_json', side_effect=AssertionError('Unauthorized read')):
                    response = cli(self, command, '--root', str(root), '--file', '/never/read')
                    self.assertEqual(response.returncode, 2, response.stderr)

    def test_pinned_changes_before_and_during_check_and_verifier_failure_never_pass(self):
        d.correct_check_reporting(self.root, self.correction)
        self.resume()
        for name in ('verify.py', '.veera-artifacts/manifest.json', '.veera-artifacts/results.json'):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.subTest(path=name), patch.object(d, 'launch', side_effect=AssertionError('No launch')):
                with self.assertRaises(ValueError):
                    d.check(self.root, 'matrix')
            self.assertFalse(d.load(self.root / '.veera').get('running'))
            path.write_bytes(original)
        active = d.load(self.root / '.veera')
        for control, expected in (('mutate', 'reporting-evidence-invalid'), ('fail', ''), ('oversized', 'output-limit')):
            d.save(self.root / '.veera', copy.deepcopy(active))
            (self.evidence / control).touch()
            result = d.check(self.root, 'matrix')
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['test_count'], 0)
            self.assertIn(expected, result['reason'])
            self.assertFalse(d.load(self.root / '.veera').get('running'))
            (self.evidence / control).unlink()
            self.write_json('results', self.results)

    def test_adapter_cannot_change_command_or_protected_paths_or_replay(self):
        for spec in ({**self.spec, 'kind': 'static'}, {**self.spec, 'argv': [sys.executable, '-c', 'print(18)']},
                     {**self.spec, 'argv': self.spec['argv'] + ['--skip-validation']}):
            with self.assertRaises(ValueError):
                reporting.validate(self.root, spec, self.adapter)
        for name in ('../escape', '.veera/state.json', '.codex/config.toml', '.env', '/absolute', 'C:/absolute'):
            with self.assertRaises(ValueError):
                reporting.read_pin(self.root, {'path': name, 'sha256': '0' * 64})
        d.correct_check_reporting(self.root, self.correction)
        before = (self.root / '.veera/state.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'already applied'):
            d.correct_check_reporting(self.root, self.correction)
        self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)

    def test_active_running_pushed_and_exhausted_corrections_fail_closed(self):
        for delta in ({'status': 'active'}, {'running': 'matrix'}, {'push_attempted': True}, {'repairs': 2}):
            d.save(self.root / '.veera', {**copy.deepcopy(self.before), **delta})
            before = (self.root / '.veera/state.json').read_bytes()
            with self.subTest(delta=delta), self.assertRaises((ValueError, d.DeliveryError)):
                d.correct_check_reporting(self.root, self.correction)
            self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)

    def test_final_validation_requires_fresh_receipt_identity(self):
        state = d.correct_check_reporting(self.root, self.correction)
        observed = reporting.validate(self.root, self.spec, self.adapter)
        result = {'status': 'passed', 'test_count': 18, 'count_source': 'verified-json-matrix',
                  'artifacts': observed['artifacts'], 'reporting_correction_id': state['reporting_corrections'][0]['id']}
        reporting.validate_result(self.root, state, self.spec, result, d.digest)
        for delta in ({'test_count': 17}, {'count_source': 'stdout'}, {'artifacts': {}}, {'reporting_correction_id': 'stale'}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                reporting.validate_result(self.root, state, self.spec, {**result, **delta}, d.digest)
