import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d
import dashboard
import safety
from session_fixture import bind, cli


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / 'app.py').write_text('value = 1\n')
        self.contract = {'scope': ['app.py'], 'non_goals': ['No deployment'], 'criteria': [{'id': 'C1', 'text': 'Tests pass', 'checks': ['unit']}], 'checks': [{'id': 'unit', 'argv': [sys.executable, '-c', "print('Ran 1 test')"], 'kind': 'test', 'count_pattern': r'Ran (\d+) test', 'timeout_seconds': 2}], 'max_repairs': 2, 'ui': False}

    def start(self, contract=None, minutes=1):
        result = d.init(self.root, 'fix', 'Fix application', contract or self.contract, minutes)
        self.session_id, self.capability = bind(self, self.root)
        return result

    def hook(self, payload):
        return safety.evaluate({'session_id': self.session_id, **payload})

    def verify_phase(self):
        for name in ('plan', 'implement', 'verify'):
            d.phase(self.root, name)

    def approve(self):
        d.phase(self.root, 'review')
        d.review(self.root, {'reviewer': 'independent-test-agent', 'notes': 'Inspected acceptance evidence', 'approved': True, 'criteria': ['C1'], 'fingerprint': d.digest(d.snapshot(self.root))})

    def test_complete_lifecycle(self):
        self.start()
        (self.root / 'app.py').write_text('value = 2\n')
        self.verify_phase()
        self.assertEqual(d.check(self.root, 'unit')['status'], 'passed')
        self.approve()
        self.assertEqual(d.finish(self.root)['status'], 'complete')

    def test_init_cannot_reset_budget(self):
        self.start()
        with self.assertRaises(d.DeliveryError):
            self.start()

    def test_zero_tests_fail(self):
        self.contract['checks'][0]['argv'][-1] = "print('Ran 0 tests')"
        self.start()
        self.verify_phase()
        self.assertEqual(d.check(self.root, 'unit')['status'], 'failed')
        self.approve()
        with self.assertRaises(d.DeliveryError):
            d.finish(self.root)

    def test_no_count_is_failure(self):
        self.contract['checks'][0]['argv'][-1] = "print('all green')"
        self.start()
        self.verify_phase()
        self.assertEqual(d.check(self.root, 'unit')['status'], 'failed')

    def test_failed_check_cannot_loop_without_repair(self):
        self.contract['checks'][0]['argv'][-1] = "print('Ran 0 tests')"
        self.start()
        self.verify_phase()
        d.check(self.root, 'unit')
        with self.assertRaises(d.DeliveryError):
            d.check(self.root, 'unit')

    def test_nonzero_exit_fails(self):
        self.contract['checks'][0]['argv'][-1] = "print('Ran 1 test'); raise SystemExit(1)"
        self.start()
        self.verify_phase()
        self.assertEqual(d.check(self.root, 'unit')['exit_code'], 1)

    def test_timeout(self):
        self.contract['checks'][0]['argv'][-1] = 'import time; time.sleep(5)'
        self.contract['checks'][0]['timeout_seconds'] = .2
        self.start()
        self.verify_phase()
        before = time.monotonic()
        result = d.check(self.root, 'unit')
        self.assertEqual(result['reason'], 'timeout')
        self.assertLess(time.monotonic() - before, 3)

    def test_stale_evidence(self):
        self.start()
        self.verify_phase()
        d.check(self.root, 'unit')
        (self.root / 'app.py').write_text('value = 3\n')
        self.approve()
        with self.assertRaises(d.DeliveryError):
            d.finish(self.root)

    def test_out_of_scope_change(self):
        self.start()
        (self.root / 'unrelated.py').write_text('x = 1\n')
        self.verify_phase()
        with self.assertRaises(d.DeliveryError):
            d.check(self.root, 'unit')

    def test_change_during_check(self):
        self.contract['checks'][0]['argv'][-1] = "from pathlib import Path; Path('app.py').write_text('changed'); print('Ran 1 test')"
        self.start()
        self.verify_phase()
        self.assertEqual(d.check(self.root, 'unit')['status'], 'failed')

    def test_repair_ceiling(self):
        self.start()
        self.verify_phase()
        for n in range(2):
            d.repair(self.root, 'new evidence ' + str(n))
            d.phase(self.root, 'verify')
        self.assertEqual(d.repair(self.root, 'third')['status'], 'blocked')

    def test_duplicate_repair_refused(self):
        self.start()
        self.verify_phase()
        d.repair(self.root, 'same')
        d.phase(self.root, 'verify')
        with self.assertRaises(d.DeliveryError):
            d.repair(self.root, 'same')

    def test_budget_exhausted_persisted(self):
        self.start(minutes=.0001)
        time.sleep(.02)
        with self.assertRaises(d.DeliveryError):
            d.phase(self.root, 'plan')
        self.assertEqual(d.status(self.root)['status'], 'budget-exhausted')

    def test_ordered_phase(self):
        self.start()
        with self.assertRaises(d.DeliveryError):
            d.phase(self.root, 'review')

    def test_bad_contracts(self):
        for scope in (['../escape'], ['/tmp/x'], ['.'], ['.git'], ['.veera']):
            contract = copy.deepcopy(self.contract)
            contract['scope'] = scope
            with self.subTest(scope=scope), self.assertRaises(d.DeliveryError):
                d.validate_contract(contract, self.root)

    def test_ui_requires_grounding(self):
        self.contract['ui'] = True
        with self.assertRaises(d.DeliveryError):
            self.start()

    def test_pm_decision(self):
        self.start()
        state = d.decision(self.root, {'owner': 'pm', 'consulted': ['architect', 'advisor'], 'decision': 'Prioritize regression', 'reason': 'Core flow affected'})
        self.assertEqual(state['events'][-1]['kind'], 'decision')
        with self.assertRaises(d.DeliveryError):
            d.decision(self.root, {'owner': 'advisor', 'consulted': [], 'decision': 'Extend budget'})

    def test_missing_review(self):
        self.start()
        self.verify_phase()
        d.check(self.root, 'unit')
        d.phase(self.root, 'review')
        with self.assertRaises(d.DeliveryError):
            d.finish(self.root)

    def test_contract_tamper_detected(self):
        self.start()
        path = self.root / d.STATE / 'state.json'
        state = d.read_json(path)
        state['contract']['scope'].append('other.py')
        path.write_text(json.dumps(state))
        with self.assertRaises(d.DeliveryError):
            d.status(self.root)

    def test_state_symlink_refused(self):
        (self.root / d.STATE).symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(d.DeliveryError):
            self.start()

    def test_stop_running_check(self):
        self.contract['checks'][0]['argv'][-1] = 'import time; time.sleep(5)'
        self.start()
        self.verify_phase()
        results = []
        thread = threading.Thread(target=lambda: results.append(d.check(self.root, 'unit')))
        thread.start()
        time.sleep(.2)
        d.stop(self.root, 'test cancellation')
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(results[0]['reason'], 'run-stopped')

    def test_visual_evidence(self):
        (self.root / '.gitignore').write_text('screens/\n')
        (self.root / 'reference.svg').write_text('<svg/>')
        self.contract['ui'] = True
        self.contract['visual_references'] = ['reference.svg']
        self.contract['checks'].append({'id': 'visual', 'kind': 'visual', 'argv': [sys.executable, '-c', "from pathlib import Path; Path('screens').mkdir(exist_ok=True); Path('screens/after.svg').write_text('<svg/>')"], 'artifacts': ['screens/after.svg']})
        self.start()
        self.verify_phase()
        d.check(self.root, 'unit')
        self.assertEqual(d.check(self.root, 'visual')['status'], 'passed')
        self.approve()
        (self.root / 'screens/after.svg').write_text('tamper')
        with self.assertRaises(d.DeliveryError):
            d.finish(self.root)

    def test_safety_scope_and_protected_files(self):
        self.start()
        def evaluate(name):
            return self.hook({'cwd': str(self.root), 'tool_name': 'Edit', 'tool_input': {'file_path': str(self.root / name)}})
        self.assertIsNone(evaluate('app.py'))
        self.assertIsNotNone(evaluate('unrelated.py'))
        self.assertIsNotNone(evaluate('.veera/state.json'))
        self.assertIsNotNone(evaluate('.env'))

    def test_safety_budget_and_dangerous_action(self):
        self.start()
        payload = {'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': 'git push origin main'}}
        self.assertIsNotNone(self.hook(payload))
        d.stop(self.root, 'done')
        payload['tool_input']['command'] = 'python3 app.py'
        self.assertIsNotNone(self.hook(payload))
        payload['tool_name'] = 'Read'
        self.assertIsNone(self.hook(payload))

    def test_unrelated_project_hook_noop(self):
        self.assertIsNone(safety.evaluate({'cwd': str(self.root), 'tool_name': 'Edit', 'tool_input': {}}))

    def test_http_dashboard(self):
        self.start()
        server, url = dashboard.create_server(self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with urllib.request.urlopen(url) as response:
            self.assertIn(b'Veera', response.read())
            self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
        with urllib.request.urlopen(url + 'status') as response:
            view = json.load(response)
            self.assertNotIn('baseline', view)
            self.assertEqual(view['status'], 'active')
        for path in ('../status', 'state.json', '../.git/config'):
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(url + path)
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(urllib.request.Request(url + 'stop', method='POST'))
        origin = url.split('/')[0] + '//' + url.split('/')[2]
        req = urllib.request.Request(url + 'stop', method='POST', headers={'Origin': origin, 'X-Delivery-Control': 'stop'})
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(d.status(self.root)['status'], 'user-stopped')

    def test_ignored_scoped_input_invalidates_evidence(self):
        (self.root / '.gitignore').write_text('app.py\n')
        self.start()
        self.verify_phase()
        d.check(self.root, 'unit')
        self.approve()
        (self.root / 'app.py').write_text('changed ignored input')
        with self.assertRaises(d.DeliveryError):
            d.finish(self.root)

    def test_failed_attempt_log_preserved(self):
        self.contract['checks'][0]['argv'][-1] = "print('Ran 0 tests')"
        self.start()
        self.verify_phase()
        first = d.check(self.root, 'unit')
        d.repair(self.root, 'Investigate fixture failure')
        d.phase(self.root, 'verify')
        second = d.check(self.root, 'unit')
        self.assertNotEqual(first['log'], second['log'])
        self.assertIn('Ran 0 tests', (self.root / d.STATE / first['log']).read_text())

    def test_fast_output_overflow_is_bounded(self):
        self.contract['checks'][0]['argv'][-1] = "import sys; sys.stdout.write('X' * (10 * 1024 * 1024)); print('Ran 1 test')"
        self.start()
        self.verify_phase()
        result = d.check(self.root, 'unit')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'output-limit')
        self.assertLessEqual((self.root / d.STATE / result['log']).stat().st_size, 8 * 1024 * 1024)

    def test_detached_stdout_holder_does_not_hang(self):
        pidfile = self.root / d.STATE / 'child.pid'
        self.contract['checks'][0]['argv'][-1] = "import subprocess,sys; from pathlib import Path; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'],start_new_session=True); Path('.veera/child.pid').write_text(str(p.pid)); print('Ran 1 test')"
        self.start()
        self.verify_phase()
        before = time.monotonic()
        try:
            bootstrap = f"import sys; from pathlib import Path; sys.path.insert(0, {str(Path(d.__file__).parent)!r}); import ownership, delivery; ownership.REGISTRY=Path({str(Path(self.capability).parent)!r}); delivery.main()"
            result = subprocess.run([sys.executable, '-c', bootstrap, 'check', '--root', str(self.root), '--id', 'unit', '--session-id', self.session_id, '--capability-file', self.capability], capture_output=True, text=True, timeout=5)
            self.assertEqual(json.loads(result.stdout)['reason'], 'output-capture-incomplete')
            self.assertEqual(result.returncode, 1)
            self.assertIsNone(d.status(self.root).get('running'))
            self.assertLess(time.monotonic() - before, 4)
        finally:
            if pidfile.exists():
                try:
                    os.kill(int(pidfile.read_text()), 9)
                except ProcessLookupError:
                    pass

    def test_old_dashboard_cannot_stop_new_run(self):
        self.start()
        server, url = dashboard.create_server(self.root)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.verify_phase()
        d.check(self.root, 'unit')
        self.approve()
        d.finish(self.root)
        d.archive(self.root)
        self.start()
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(url + 'status')
        self.assertEqual(caught.exception.code, 410)
        origin = 'http://' + url.split('/')[2]
        request = urllib.request.Request(url + 'stop', method='POST', headers={'Origin': origin, 'X-Delivery-Control': 'stop'})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code, 410)
        self.assertEqual(d.status(self.root)['status'], 'active')

    def test_real_bug_fix_lifecycle(self):
        (self.root / 'app.py').write_text('def add(a, b):\n    return a - b\n')
        (self.root / 'test_app.py').write_text('import unittest\nfrom app import add\nclass Tests(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n')
        (self.root / '.gitignore').write_text('__pycache__/\n')
        self.contract['checks'][0]['argv'] = [sys.executable, '-B', '-m', 'unittest', 'test_app', '-v']
        self.start()
        self.verify_phase()
        result = d.check(self.root, 'unit')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['test_count'], 1)
        d.repair(self.root, 'Assertion showed subtraction instead of addition')
        (self.root / 'app.py').write_text('def add(a, b):\n    return a + b\n')
        d.phase(self.root, 'verify')
        self.assertEqual(d.check(self.root, 'unit')['status'], 'passed')
        self.approve()
        self.assertEqual(d.finish(self.root)['status'], 'complete')
        archived = d.archive(self.root)
        self.assertEqual(archived['status'], 'archived')
        self.assertTrue(Path(archived['path'], 'state.json').exists())
        self.start()  # A distinct task can start only after completed-run archival.

    def test_archive_cannot_renew_incomplete_budget(self):
        self.start()
        d.stop(self.root, 'incomplete')
        with self.assertRaises(d.DeliveryError):
            d.archive(self.root)

    def test_terminal_hook_allows_exact_status_not_shell_chain(self):
        self.start()
        d.stop(self.root, 'stop')
        command = f'python3 {d.__file__} status --root {self.root}'
        payload = {'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': command}}
        self.assertIsNone(self.hook(payload))
        payload['tool_input']['command'] += '; python3 app.py'
        self.assertIsNotNone(self.hook(payload))

    def test_evidence_write_allowed(self):
        self.start()
        payload = {'cwd': str(self.root), 'tool_name': 'Write', 'tool_input': {'file_path': str(self.root / '.veera-artifacts/review.json')}}
        self.assertIsNone(self.hook(payload))

    def test_cli_roundtrip(self):
        self.start()
        result = cli(self, 'status', '--root', str(self.root))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)['mode'], 'fix')


if __name__ == '__main__':
    unittest.main()
