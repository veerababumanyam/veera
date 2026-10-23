import copy
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import dashboard
from delivery import atomic, locked


class DashboardLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = {'run_id': 'lifecycle-fixture', 'status': 'active'}
        self.status_patch = patch.object(dashboard, 'status', side_effect=lambda root: copy.deepcopy(self.state))
        self.status_patch.start()
        self.addCleanup(self.status_patch.stop)

    def record(self, url, run_id='lifecycle-fixture'):
        with locked(self.root) as directory:
            atomic(directory / 'dashboard.json', {'dashboard_url': url, 'run_id': run_id})

    def test_only_live_current_task_url_is_returned(self):
        self.assertEqual(dashboard.info(self.root)['status'], 'not-started')
        server, url = dashboard.create_server(self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.record(url)
            result = dashboard.info(self.root)
            self.assertEqual(result['dashboard_url'], url)
            self.assertTrue(Path(result['record_path']).is_absolute())
            self.assertEqual(result['status'], 'running')
            self.state['run_id'] = 'replacement'
            self.assertEqual(dashboard.info(self.root)['status'], 'stale')
            self.assertIsNone(dashboard.info(self.root)['dashboard_url'])
            self.state['run_id'] = 'lifecycle-fixture'
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)
        result = dashboard.info(self.root)
        self.assertEqual(result['status'], 'not-running')
        self.assertIsNone(result['dashboard_url'])

    def test_saved_address_cannot_redirect_to_an_external_service(self):
        for url in ('https://example.com/', 'http://127.0.0.1:80@evil.invalid/', 'file:///secret', 'http://localhost:8000/token/'):
            self.record(url)
            with patch.object(dashboard, 'build_opener', side_effect=AssertionError('No connection allowed')):
                with self.assertRaises(ValueError):
                    dashboard.info(self.root)
        with locked(self.root) as directory:
            atomic(directory / 'dashboard.json', [])
        with self.assertRaisesRegex(ValueError, 'record'):
            dashboard.info(self.root)

    def test_server_automatically_opens_and_reuses_browser_address(self):
        self.run_server(open_browser=True)

    def test_headless_server_records_address_without_opening_browser(self):
        self.run_server(open_browser=False)

    def run_server(self, open_browser):
        ready = threading.Event()
        servers = []
        original = dashboard.create_server

        def create(*args):
            server, url = original(*args)
            servers.append(server)
            return server, url

        def output(*args, **kwargs):
            ready.set()

        with patch.object(dashboard, 'create_server', side_effect=create), patch.object(dashboard.webbrowser, 'open', return_value=True) as browser, patch('builtins.print', side_effect=output):
            worker = threading.Thread(target=dashboard.serve, args=(self.root,), kwargs={'open_browser': open_browser}, daemon=True)
            worker.start()
            try:
                self.assertTrue(ready.wait(3), 'Dashboard failed to start')
                result = dashboard.info(self.root)
                self.assertEqual(result['status'], 'running')
                if open_browser:
                    # The running HTTP response also gives the opener thread time to run.
                    browser.assert_called_with(result['dashboard_url'], new=2)
                else:
                    browser.assert_not_called()
                with patch.object(dashboard, 'create_server', side_effect=AssertionError('Duplicate server')):
                    dashboard.serve(self.root, open_browser=False)
                self.assertEqual(len(servers), 1)
            finally:
                if servers:
                    servers[0].shutdown()
                worker.join(3)
                self.assertFalse(worker.is_alive())
