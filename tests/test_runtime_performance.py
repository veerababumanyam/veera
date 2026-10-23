"""Behavioral regression guards for the measured status hot path."""
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d


class StatusIOTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / 'app.py').write_text('value = 1\n')
        self.contract = {'scope': ['app.py'], 'criteria': [{'id': 'C1', 'text': 'Fixture', 'checks': ['unit']}],
                         'checks': [{'id': 'unit', 'kind': 'test', 'argv': [sys.executable, '-m', 'unittest'], 'count_pattern': r'Ran (\d+) test'}]}
        d.init(self.root, 'fix', 'Status fixture', self.contract, 10)

    def test_unchanged_status_reads_never_rewrite_state(self):
        before = (self.root / '.veera/state.json').stat().st_mtime_ns
        with patch.object(d, 'save', wraps=d.save) as save:
            for _ in range(3):
                self.assertEqual(d.status(self.root)['status'], 'active')
            save.assert_not_called()
        self.assertEqual((self.root / '.veera/state.json').stat().st_mtime_ns, before)

    def test_soft_and_hard_expiry_are_persisted_once(self):
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state['soft_deadline'] = time.time() - 1
            d.save(directory, state)
        with patch.object(d, 'save', wraps=d.save) as save:
            self.assertTrue(d.status(self.root)['replan_required'])
            d.status(self.root)
            self.assertEqual(save.call_count, 1)
        with d.locked(self.root) as directory:
            state = d.load(directory)
            self.assertEqual(sum(event['kind'] == 'replan' for event in state['events']), 1)
            state['deadline'] = time.time() - 1
            d.save(directory, state)
        with patch.object(d, 'save', wraps=d.save) as save:
            self.assertEqual(d.status(self.root)['status'], 'budget-exhausted')
            d.status(self.root)
            self.assertEqual(save.call_count, 1)
        with d.locked(self.root) as directory:
            self.assertEqual(d.load(directory)['status'], 'budget-exhausted')

    def test_every_read_still_rejects_contract_tampering(self):
        d.status(self.root)
        with d.locked(self.root) as directory:
            state = d.load(directory)
            state['contract']['scope'].append('other.py')
            d.save(directory, state)
        with self.assertRaisesRegex(d.DeliveryError, 'integrity'):
            d.status(self.root)
