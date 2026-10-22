import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import model_router as r


class AutoRouterTests(unittest.TestCase):
    def test_risk_wins_over_routine_words(self):
        for task in ('Summarize security permissions', 'Format production deployment configuration',
                     'Small edit to concurrent ownership', 'Review final release',
                     'Document a database migration',
                     'Summarize README, then design a payment transaction rollback strategy',
                     'List files and decide how to store encryption keys'):
            self.assertEqual(r.select(task)['tier'], 'important', task)

    def test_routine_and_unknown(self):
        for task in ('Summarize README', 'List files in docs', 'Format markdown', 'Run established checks'):
            self.assertEqual(r.select(task)['model'], 'gpt-6.1-sol')
        self.assertEqual(r.select('Make it work')['model'], 'gpt-6-astra')

    def test_both_hosts_use_codex_without_permission_bypass(self):
        for host in ('codex', 'claude'):
            cmd = r.command('codex', Path.cwd(), r.select('Summarize README'))
            self.assertIn('read-only', cmd)
            self.assertIn('gpt-6.1-sol', cmd)
            self.assertNotIn('resume', cmd)
            self.assertFalse(any('bypass' in x for x in cmd))

    def test_failure_never_falls_back(self):
        failure = subprocess.CompletedProcess([], 1, '{"type":"error","message":"unavailable"}\n', '')
        with patch.object(r.subprocess, 'run', return_value=failure) as run:
            result = r.execute('Review security', Path.cwd(), 'claude', executable='codex')
        self.assertEqual(run.call_count, 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['selection']['model'], 'gpt-6-astra')

    def test_no_false_execution_verification(self):
        output = '\n'.join(json.dumps(x) for x in [
            {'type': 'thread.started', 'thread_id': 'fixture-only'},
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'done'}},
            {'type': 'turn.completed'}])
        with patch.object(r.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output, '')):
            result = r.execute('Summarize README', Path.cwd(), 'codex', executable='codex')
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(result['actual_model_verified'])
        self.assertEqual(result['response'], 'done')

    def test_recursion_and_empty_rejected(self):
        with self.assertRaises(ValueError):
            r.select('  ')
        with patch.dict(r.os.environ, {'VEERA_ROUTER_ACTIVE': '1'}):
            with self.assertRaises(ValueError):
                r.execute('Summarize README', Path.cwd(), 'codex')
