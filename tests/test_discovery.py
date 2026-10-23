"""Traceability, answered interviews, immutability and legacy compatibility."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d
import discovery
import dashboard_documents as docs


def example():
    return {'version': 1, 'request': 'Reject invalid quantities', 'outcome': 'Invalid quantities produce a domain error',
            'domain': 'Order quantities are positive integers',
            'evidence': [{'id': 'E1', 'kind': 'user-request', 'source': 'Fixture user message', 'finding': 'Reject invalid quantities'},
                         {'id': 'E2', 'kind': 'code', 'source': 'app.py:1', 'finding': 'Validation is missing'}],
            'requirements': [{'id': 'R1', 'text': 'Reject zero', 'basis': 'project-evidence', 'evidence_ids': ['E1', 'E2'], 'criteria': ['C1']}],
            'assumptions': [], 'non_goals': ['Other order flows'], 'questions': [],
            'plan': [{'id': 'P1', 'action': 'Add validation and verify zero is rejected', 'requirement_ids': ['R1'], 'checks': ['unit']}],
            'open_questions': []}


def question():
    return {'id': 'Q1', 'question': 'How should invalid quantities be handled?',
            'options': [{'id': 'reject', 'label': 'Reject (recommended)', 'tradeoff': 'Preserve explicit errors'},
                        {'id': 'coerce', 'label': 'Coerce', 'tradeoff': 'May hide mistakes'}],
            'recommendation': 'reject', 'rationale': 'Existing order errors use the domain error type',
            'evidence_ids': ['E2'], 'answer': 'Reject', 'answer_source': 'Fixture user response', 'resolved_by': 'user'}


class DiscoveryTests(unittest.TestCase):
    def validate(self, value):
        discovery.validate(value, {'C1'}, {'unit'})

    def test_brief_with_answered_options_or_free_text(self):
        value = example()
        self.validate(value)
        value['questions'] = [question()]
        self.validate(value)
        value['questions'][0].update(options=[], recommendation='', answer='Custom behavior')
        self.validate(value)

    def test_essential_questions_and_unanswered_choices_block_lock(self):
        value = example()
        value['open_questions'] = ['Missing destination']
        with self.assertRaisesRegex(ValueError, 'before implementation'):
            self.validate(value)
        for key in ('answer', 'answer_source', 'rationale'):
            value = example()
            value['questions'] = [{**question(), key: ''}]
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(value)

    def test_recommendations_must_name_real_options_and_evidence(self):
        for field, bad in (('recommendation', 'invented'), ('options', [question()['options'][0]]),
                           ('evidence_ids', ['unknown']), ('resolved_by', 'pretend-user')):
            value = example()
            value['questions'] = [{**question(), field: bad}]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(value)

    def test_references_and_full_coverage(self):
        for section, field, bad in (('requirements', 'criteria', ['unknown']), ('requirements', 'evidence_ids', ['unknown']),
                                    ('plan', 'requirement_ids', ['unknown']), ('plan', 'checks', ['unknown']),
                                    ('requirements', 'evidence_ids', ['E1', 'E1'])):
            value = example()
            value[section][0][field] = bad
            with self.subTest(section=section, field=field), self.assertRaises(ValueError):
                self.validate(value)
        with self.assertRaisesRegex(ValueError, 'acceptance criterion'):
            discovery.validate(example(), {'C1', 'C2'}, {'unit'})
        with self.assertRaisesRegex(ValueError, 'frozen checks'):
            discovery.validate(example(), {'C1'}, {'unit', 'integration'})
        value = example()
        value['requirements'].append({**value['requirements'][0], 'id': 'R2'})
        with self.assertRaisesRegex(ValueError, 'all requirements'):
            self.validate(value)

    def test_missing_project_evidence_duplicate_ids_and_unrecorded_assumptions(self):
        for change in ('evidence', 'duplicate', 'assumption'):
            value = example()
            if change == 'evidence':
                value['evidence'] = value['evidence'][:1]
            elif change == 'duplicate':
                value['evidence'].append(value['evidence'][0])
            else:
                value['requirements'][0]['basis'] = 'assumption'
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.validate(value)

    def test_malformed_unknown_and_unbounded_data(self):
        for value in (None, [], {'version': 1}, {**example(), 'approved': True},
                      {**example(), 'version': True}, {**example(), 'domain': 'x' * 2001},
                      {**example(), 'assumptions': ['x'] * 31}, {**example(), 'plan': [None]}):
            with self.subTest(value_type=type(value)), self.assertRaises(ValueError):
                self.validate(value)
        value = example()
        for key in ('assumptions', 'non_goals'):
            value[key] = ['x' * 2000] * 30
        value['domain'] = '\U0001f600' * 2000
        value['request'] = '\U0001f600' * 2000
        with self.assertRaisesRegex(ValueError, '128 KiB'):
            self.validate(value)

    def test_init_persists_brief_and_rejects_unresolved_or_tampered_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'app.py').write_text('quantity = 1\n')
            contract = {'scope': ['app.py'], 'criteria': [{'id': 'C1', 'text': 'Reject zero', 'checks': ['unit']}],
                        'checks': [{'id': 'unit', 'kind': 'static', 'argv': [sys.executable, '--version']}], 'discovery': example()}
            bad = copy.deepcopy(contract)
            bad['discovery']['open_questions'] = ['Which behavior?']
            with self.assertRaises(d.DeliveryError):
                d.init(root, 'fix', 'Fixture', bad, 1)
            self.assertFalse((root / '.veera/state.json').exists())
            state = d.init(root, 'fix', 'Fixture', contract, 1)
            self.assertEqual(d.status(root)['contract']['discovery'], example())
            state['contract']['discovery']['request'] = 'Changed request'
            d.atomic(root / '.veera/state.json', state)
            with self.assertRaisesRegex(d.DeliveryError, 'integrity'):
                d.status(root)

    def test_legacy_contract_and_html_show_no_invented_research(self):
        self.assertIn('No requirements', docs.document('task-discovery', {'contract': {}})['html'])
        value = example()
        value['request'] = '<script>bad()</script>'
        html = docs.document('task-discovery', {'contract': {'discovery': value}})['html']
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        with tempfile.TemporaryDirectory() as directory:
            contract = {'scope': ['app.py'], 'criteria': [{'id': 'C1', 'text': 'Legacy', 'checks': ['unit']}],
                        'checks': [{'id': 'unit', 'kind': 'static', 'argv': ['python', '--version']}]}
            d.validate_contract(contract, Path(directory).resolve())
            for malformed in (None, 7, []):
                with self.assertRaisesRegex(d.DeliveryError, 'object'):
                    d.validate_contract(malformed, Path(directory).resolve())

    def test_amendment_appends_without_mutating_original_or_overriding_outcome(self):
        original = example()
        before = copy.deepcopy(original)
        amended = discovery.append(original, {'requirements': [{'id': 'R2', 'text': 'Reject negative', 'basis': 'user-request',
                                                                'evidence_ids': ['E1'], 'criteria': ['C2']}],
                                               'plan': [{'id': 'P2', 'action': 'Verify negatives', 'requirement_ids': ['R2'], 'checks': ['negative']}]})
        discovery.validate(amended, {'C1', 'C2'}, {'unit', 'negative'})
        self.assertEqual(original, before)
        for additions in ({'outcome': 'Replacement'}, {'questions': {}}, {}, None):
            with self.assertRaises(ValueError):
                discovery.append(original, additions)
