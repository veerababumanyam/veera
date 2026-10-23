"""Explicit allowance grants use disposable owners; never reset spent rounds."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_amend as fixtures
import delivery as d
from session_fixture import cli


class RepairExtensionTests(unittest.TestCase):
    setUp = fixtures.AmendmentTests.setUp

    def grant_report(self):
        return {'run_id': self.before['run_id'], 'checkpoint_id': self.before['checkpoint']['id'],
                'expected_contract_hash': self.before['contract_hash'], 'expected_limit': 2,
                'expected_repairs': 0, 'additional_repairs': 20, 'authorization_id': 'human-message-17',
                'authorization': 'Explicit fixture user approval for 20 more rounds', 'reason': 'Remaining work'}

    def test_grant_preserves_state_and_delays_time_until_resume(self):
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state.update(repairs=2, deadline=1, usage={'cost_usd': 12},
                         checks={'unit': {'status': 'failed'}}, blockers={'saved': {'limit': 2, 'attempts': [1, 2]}})
            d.save(directory, state)
        owner = Path(self.capability).read_bytes()
        report = {**self.grant_report(), 'expected_repairs': 2}
        # Reports belong in ignored evidence, not the checkpointed source.
        report_path = self.root / '.veera-artifacts/grant.json'
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(json.dumps(report))
        result = cli(self, 'extend-repairs', '--root', str(self.root), '--file', str(report_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        after = d.status(self.root)
        for key in ('repairs', 'deadline', 'started_at', 'contract', 'contract_hash', 'checks', 'blockers', 'usage', 'status'):
            self.assertEqual(after[key], state[key], key)
        self.assertEqual(d.repair_limit(after), 22)
        self.assertEqual(after['repair_extensions'][0]['report'], report)
        self.assertEqual(after['events'][:-1], state['events'])
        self.assertEqual(Path(self.capability).read_bytes(), owner)
        with patch.object(d.time, 'time', return_value=10000):
            resumed = d.resume(self.root, {'checkpoint_id': state['checkpoint']['id'], 'authorization': '300 minutes approved',
                'reason': 'Ready now', 'additional_minutes': 300,
                'time_plan': [{'id': 'remaining', 'criterion_id': 'C1', 'minutes': 300, 'reason': 'Remaining implementation and verification'}]})
        self.assertEqual(resumed['deadline'], 28000)
        self.assertEqual(resumed['repairs'], 2)
        self.assertEqual(d.repair_limit(resumed), 22)
        with patch.object(d.time, 'time', return_value=10001):
            d.phase(self.root, 'verify')
            repaired = d.repair(self.root, 'Distinct correction after explicit grant')
        self.assertEqual(repaired['repairs'], 3)
        self.assertEqual(repaired['blockers']['saved']['limit'], 2)

    def test_invalid_or_replayed_grants_do_not_write(self):
        for delta in ({'additional_repairs': True}, {'additional_repairs': 0}, {'additional_repairs': -1},
                      {'additional_repairs': 1.5}, {'expected_limit': 3}, {'expected_repairs': 1},
                      {'run_id': 'foreign'}, {'checkpoint_id': 'stale'}, {'expected_contract_hash': 'stale'},
                      {'authorization': ''}, {'authorization_id': ''}, {'deadline': 999999}):
            before = (self.root / '.veera/state.json').read_bytes()
            with self.subTest(delta=delta), self.assertRaises(d.DeliveryError):
                d.extend_repairs(self.root, {**self.grant_report(), **delta})
            self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)
        d.extend_repairs(self.root, self.grant_report())
        before = (self.root / '.veera/state.json').read_bytes()
        for report in (self.grant_report(), {**self.grant_report(), 'expected_limit': 22}):
            with self.assertRaises(d.DeliveryError):
                d.extend_repairs(self.root, report)
            self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)

    def test_active_running_publication_or_changed_source_denied(self):
        for delta in ({'status': 'active'}, {'running': 'unit'}, {'push_attempted': True}):
            state = {**copy.deepcopy(self.before), **delta}
            d.save(self.root / '.veera', state)
            before = (self.root / '.veera/state.json').read_bytes()
            with self.assertRaises(d.DeliveryError):
                d.extend_repairs(self.root, self.grant_report())
            self.assertEqual((self.root / '.veera/state.json').read_bytes(), before)
        d.save(self.root / '.veera', self.before)
        (self.root / 'app.py').write_text('changed')
        with self.assertRaises(d.DeliveryError):
            d.extend_repairs(self.root, self.grant_report())
