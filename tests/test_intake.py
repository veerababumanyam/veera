"""Intake captures intent, never permission grants or a second task state store."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d
import intake
import dashboard_documents as docs


def example():
    return {'version': 1, 'user_request_ref': 'fixture user request',
            'authorized_actions': [{'action': 'Edit and test', 'scope': 'app.py', 'evidence': 'fixture request'}],
            'delegated_decisions': [{'topic': 'Sequencing', 'owner': 'pm', 'limits': 'Keep scope and ceilings'}],
            'known_inputs': [{'name': 'Goal', 'value': 'Fix app.py', 'source': 'fixture user request'}],
            'assumptions': [], 'open_questions': [], 'escalation': 'block-affected-work',
            'native_approval': 'required-where-applicable'}


class IntakeTests(unittest.TestCase):
    def test_valid_record_and_internal_roles(self):
        for role in ('pm', 'architect', 'advisor', 'orchestrator'):
            value = example()
            value['delegated_decisions'][0]['owner'] = role
            intake.validate(value)

    def test_no_permission_override_or_blanket_host_approval(self):
        for key, value in (('native_approval', 'preapproved'), ('escalation', 'ask-advisor'),
                           ('version', True), ('user_request_ref', '')):
            data = example()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                intake.validate(data)
        data = example()
        data['permission_granted'] = True
        with self.assertRaises(ValueError):
            intake.validate(data)

    def test_missing_fields_and_unresolved_questions_are_rejected(self):
        for key in example():
            value = example()
            del value[key]
            with self.subTest(key=key), self.assertRaises(ValueError):
                intake.validate(value)
        value = example()
        value['open_questions'] = ['Which repository?']
        with self.assertRaisesRegex(ValueError, 'before freezing'):
            intake.validate(value)

    def test_malformed_or_unbounded_entries_are_rejected(self):
        for field, value in (('assumptions', ['x' * 2001]), ('known_inputs', [None]),
                             ('delegated_decisions', [{'topic': 'Auth', 'owner': 'user-proxy', 'limits': 'none'}]),
                             ('authorized_actions', ['all']), ('assumptions', ['x'] * 31)):
            data = example()
            data[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                intake.validate(data)

    def test_frozen_record_is_persisted_and_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'app.py').write_text('value = 1\n')
            contract = {'scope': ['app.py'], 'criteria': [{'id': 'C1', 'text': 'Fixture', 'checks': ['check']}],
                        'checks': [{'id': 'check', 'kind': 'static', 'argv': [sys.executable, '--version']}], 'intake': example()}
            state = d.init(root, 'fix', 'Fixture only', contract, 1)
            self.assertEqual(d.status(root)['contract']['intake'], example())
            state['contract']['intake']['authorized_actions'].append({'action': 'Publish', 'scope': 'all', 'evidence': 'invented'})
            d.atomic(root / '.veera/state.json', state)
            with self.assertRaises(d.DeliveryError):
                d.status(root)

    def test_intake_display_preserves_evidence_as_text(self):
        value = example()
        value['user_request_ref'] = '<script>fake approval</script>'
        result = docs.document('task-intake', {'contract': {'intake': value}})
        self.assertIn('&lt;script&gt;', result['html'])
        self.assertNotIn('<script>', result['html'])
        self.assertIn('required-where-applicable', result['html'])

    def test_legacy_task_has_no_inferred_authority(self):
        self.assertIn('No intake', docs.document('task-intake', {'contract': {}})['html'])
