"""Campaign inputs move forward without replacing historical evidence."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_check_reporting as fixtures
import delivery as d
import check_reporting as reporting
from session_fixture import cli


class RebindingTests(unittest.TestCase):
    pin = fixtures.ReportingTests.pin
    write_json = fixtures.ReportingTests.write_json
    resume = fixtures.ReportingTests.resume

    def setUp(self):
        fixtures.ReportingTests.setUp(self)
        d.extend_repairs(self.root, {'run_id': self.before['run_id'], 'checkpoint_id': self.before['checkpoint']['id'],
            'expected_contract_hash': self.before['contract_hash'], 'expected_limit': 2, 'expected_repairs': 1,
            'additional_repairs': 3, 'authorization_id': 'fixture-extra-repairs',
            'authorization': 'Fixture explicit repair allowance', 'reason': 'Separate recovery steps'})
        self.before = d.load(self.root / '.veera')
        self.before.update(usage={'cost_usd': 12, 'cap_usd': 50},
                           blockers={'saved': {'status': 'resolved', 'limit': 3, 'attempts': [{'outcome': 'failed'}]}})
        d.save(self.root / '.veera', self.before)
        self.write_json('final-manifest', {**self.manifest, 'campaign_id': 'fixture-final'})
        self.write_json('final-results', {**self.results, 'campaign_id': 'fixture-final'})
        self.new_inputs = {key: self.pin('.veera-artifacts/final-' + key + '.json') for key in ('manifest', 'results')}
        self.new_spec = copy.deepcopy(self.spec)
        self.new_spec['argv'][-3] = self.new_inputs['manifest']['path']
        self.new_spec['argv'][-1] = self.new_inputs['results']['path']
        binding = {'verifier': self.adapter['verifier'],
                   'prior_inputs': {key: self.adapter[key] for key in ('manifest', 'results')}, 'inputs': self.new_inputs}
        self.rebinding = {'run_id': self.before['run_id'], 'checkpoint_id': self.before['checkpoint']['id'],
            'expected_contract_hash': self.before['contract_hash'], 'check_id': 'matrix',
            'expected_check_hash': d.digest(self.spec), 'expected_checks_hash': d.digest(self.before['checks']),
            'authorization_id': 'fixture-human-inputs', 'authorization': 'Explicit new evidence paths approval',
            'reason': 'Keep old campaign evidence in place', **binding,
            'review': {'reviewer': 'separate-fixture-reviewer', 'notes': 'Same verifier and criteria; fresh complete campaign',
                      'approved': True, 'fingerprint': self.before['checkpoint']['fingerprint'],
                      'prior_check_hash': d.digest(self.spec), 'new_check_hash': d.digest(self.new_spec),
                      'binding_hash': d.digest(binding)}}

    def test_public_rebind_preserves_artifacts_contract_except_two_paths_and_all_history(self):
        old_files = {key: (self.root / self.adapter[key]['path']).read_bytes() for key in ('manifest', 'results')}
        owner = Path(self.capability).read_bytes()
        report_path = self.evidence / 'rebind.json'
        report_path.write_text(json.dumps(self.rebinding))
        response = cli(self, 'rebind-check-inputs', '--root', str(self.root), '--file', str(report_path))
        self.assertEqual(response.returncode, 0, response.stderr)
        state = d.load(self.root / '.veera')
        expected_contract = copy.deepcopy(self.before['contract'])
        expected_contract['checks'] = [self.new_spec]
        self.assertEqual(state['contract'], expected_contract)
        self.assertEqual(state['contract_hash'], d.digest(expected_contract))
        for key in set(self.before) - {'contract', 'contract_hash', 'checks', 'review', 'events', 'updated_at'}:
            self.assertEqual(state[key], self.before[key], key)
        self.assertEqual(state['events'][:-1], self.before['events'])
        receipt = state['input_rebindings'][0]
        self.assertEqual(receipt['prior_contract'], self.before['contract'])
        self.assertEqual(receipt['prior_contract_hash'], self.before['contract_hash'])
        self.assertEqual(receipt['prior_checks'], self.before['checks'])
        self.assertEqual(receipt['prior_check'], self.spec)
        self.assertEqual(receipt['new_check'], self.new_spec)
        self.assertEqual(state['checks'], {})
        self.assertIsNone(state['review'])
        self.assertEqual(Path(self.capability).read_bytes(), owner)
        for key, content in old_files.items():
            self.assertEqual((self.root / self.adapter[key]['path']).read_bytes(), content)
        self.resume()
        failed = d.check(self.root, 'matrix')
        self.assertEqual((failed['status'], failed['exit_code'], failed['test_count']), ('failed', 0, 0))
        self.assertEqual(failed['argv'], self.new_spec['argv'])
        self.assertEqual(failed['input_rebinding_id'], receipt['id'])
        # A separate bounded repair, reviewed correction and fresh check remain necessary.
        d.repair(self.root, 'Correct missing count for finalized campaign')
        d.stop(self.root, 'Apply reviewed count correction')
        self.before = d.checkpoint(self.root, 'Final campaign count-only failure')
        adapter = {'kind': 'verified-json-matrix', 'verifier': self.adapter['verifier'], **self.new_inputs}
        correction = {**self.correction, 'checkpoint_id': self.before['checkpoint']['id'],
            'expected_contract_hash': self.before['contract_hash'], 'expected_check_hash': d.digest(self.new_spec),
            'expected_result_hash': d.digest(failed), 'adapter': adapter,
            'log_sha256': hashlib.sha256((self.root / '.veera' / failed['log']).read_bytes()).hexdigest(),
            'review': {**self.correction['review'], 'check_hash': d.digest(self.new_spec), 'adapter_hash': d.digest(adapter)}}
        d.correct_check_reporting(self.root, correction)
        self.resume()
        passed = d.check(self.root, 'matrix')
        self.assertEqual((passed['status'], passed['test_count']), ('passed', 18))
        state = d.load(self.root / '.veera')
        reporting.validate_result(self.root, state, self.new_spec, passed, d.digest)
        with self.assertRaisesRegex(ValueError, 'rebound check evidence'):
            reporting.validate_result(self.root, state, self.new_spec, {**passed, 'input_rebinding_id': 'old'}, d.digest)
        (self.root / self.adapter['manifest']['path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Pinned evidence changed'):
            reporting.validate_result(self.root, state, self.new_spec, passed, d.digest)

    def test_stale_authority_reviews_and_extra_mutations_write_nothing(self):
        deltas = [{'run_id': 'foreign'}, {'checkpoint_id': 'old'}, {'expected_contract_hash': 'old'},
                  {'expected_check_hash': 'old'}, {'expected_checks_hash': 'old'}, {'authorization_id': ''}, {'authorization': ''},
                  {'argv': ['replacement']}, {'kind': 'static'}, {'count_pattern': '(1)'}, {'timeout_seconds': 999},
                  {'criteria': []}, {'deadline': 999}, {'check_id': 'other'}, {'review': {}},
                  {'review': {**self.rebinding['review'], 'approved': False}},
                  {'review': {**self.rebinding['review'], 'binding_hash': 'old'}},
                  {'inputs': {**self.new_inputs, 'manifest': self.adapter['manifest']}},
                  {'prior_inputs': self.new_inputs}, {'verifier': self.new_inputs['manifest']}]
        for delta in deltas:
            before = (self.root / '.veera/state.json').read_bytes()
            with self.subTest(delta=delta), self.assertRaises((ValueError, d.DeliveryError)):
                d.rebind_check_inputs(self.root, {**self.rebinding, **delta})
            self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)
        d.rebind_check_inputs(self.root, self.rebinding)
        before = (self.root / '.veera/state.json').read_bytes()
        report = {**self.rebinding, 'expected_contract_hash': d.load(self.root / '.veera')['contract_hash']}
        with self.assertRaisesRegex(ValueError, 'already applied'):
            d.rebind_check_inputs(self.root, report)
        self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)
        state = d.load(self.root / '.veera')
        reuse = {**report, 'authorization_id': 'fixture-second-approval',
                 'expected_check_hash': d.digest(self.new_spec), 'expected_checks_hash': d.digest(state['checks']),
                 'prior_inputs': self.new_inputs, 'inputs': self.rebinding['prior_inputs']}
        with self.assertRaisesRegex(ValueError, 'previously unused paths'):
            d.rebind_check_inputs(self.root, reuse)
        self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)

    def test_non_recovery_states_unspent_repair_and_changed_source_are_denied(self):
        for delta in ({'status': 'active'}, {'running': 'matrix'}, {'push_attempted': True}, {'repairs': 5}, {'repairs': 0}):
            d.save(self.root / '.veera', {**copy.deepcopy(self.before), **delta})
            before = (self.root / '.veera/state.json').read_bytes()
            with self.subTest(delta=delta), self.assertRaises((ValueError, d.DeliveryError)):
                d.rebind_check_inputs(self.root, self.rebinding)
            self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)
        d.save(self.root / '.veera', self.before)
        (self.root / 'app.py').write_text('changed')
        with self.assertRaisesRegex(d.DeliveryError, 'source changed'):
            d.rebind_check_inputs(self.root, self.rebinding)

    def test_foreign_owner_denied_before_report_read(self):
        for session, capability, root in [('foreign', self.capability, self.root),
                (self.session_id, '/wrong', self.root), (self.session_id, self.capability, self.root.parent)]:
            with self.subTest(session=session), patch.object(self, 'session_id', session), \
                 patch.object(self, 'capability', capability), patch.object(d, 'read_json', side_effect=AssertionError('Unauthorized read')):
                result = cli(self, 'rebind-check-inputs', '--root', str(root), '--file', '/never/read')
                self.assertEqual(result.returncode, 2, result.stderr)

    def test_historical_and_new_pin_mutations_fail_before_and_during_execution(self):
        d.rebind_check_inputs(self.root, self.rebinding)
        self.resume()
        for ref in [self.adapter['verifier'], *self.rebinding['prior_inputs'].values(), *self.new_inputs.values()]:
            path = self.root / ref['path']
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.subTest(path=ref['path']), patch.object(d, 'launch', side_effect=AssertionError('No execution')):
                with self.assertRaisesRegex(ValueError, 'Pinned evidence changed'):
                    d.check(self.root, 'matrix')
            self.assertFalse(d.load(self.root / '.veera').get('running'))
            path.write_bytes(original)
        (self.evidence / 'mutate').touch()
        result = d.check(self.root, 'matrix')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('rebound-evidence-invalid', result['reason'])
        self.assertFalse(d.load(self.root / '.veera').get('running'))

    def test_rebinding_cannot_reuse_a_reporting_corrected_check(self):
        d.correct_check_reporting(self.root, self.correction)
        state = d.load(self.root / '.veera')
        before = (self.root / '.veera/state.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'reporting-corrected'):
            d.rebind_check_inputs(self.root, {**self.rebinding, 'expected_checks_hash': d.digest(state['checks'])})
        self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)
