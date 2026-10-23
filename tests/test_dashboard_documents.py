import copy
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import dashboard
import dashboard_documents as docs


class DashboardDocumentsTests(unittest.TestCase):
    def setUp(self):
        self.state = {'run_id': 'fixture-run', 'contract': {'criteria': [{'id': 'C1', 'text': '<script>bad()</script>'}], 'scope': ['app.py']}, 'events': []}

    def test_task_document_escapes_untrusted_fields(self):
        result = docs.document('task-contract', self.state)
        self.assertNotIn('<script>', result['html'])
        self.assertIn('&lt;script&gt;', result['html'])

    def test_missing_records_are_explicit_not_success(self):
        for key in ('task-review', 'task-decisions', 'task-memory', 'task-checkpoint'):
            self.assertIn('recorded yet', docs.document(key, self.state)['html'])

    def test_markdown_does_not_execute_html_or_external_links(self):
        html = docs.markdown('# Title\n\n<script>alert(1)</script>\n\n[x](javascript:alert)\n\n[x](https://example.invalid)\n\n```html\n<img onerror=x>\n```')
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img', html)
        self.assertNotIn('href=', html)
        self.assertIn('<h2>Title</h2>', html)
        self.assertIn('<pre><code>', html)

    def test_markdown_tables_lists_and_local_document_links(self):
        html = docs.markdown('| Name | State |\n| --- | --- |\n| Check | Passed |\n\n- One\n- Two\n\n[Contract](docs/agent-contract.md)', docs.ROOT / 'README.md')
        self.assertIn('<table>', html)
        self.assertIn('<li>Two</li>', html)
        self.assertIn('href="?doc=guide-', html)

    def test_documents_are_an_id_allowlist_not_a_file_server(self):
        for key in ('../.env', '.veera/state.json', 'guide-../../README.md', '/etc/passwd', 'C:/secrets.txt', 'task-review/../'):
            with self.assertRaises(KeyError):
                docs.document(key, self.state)

    def test_all_packaged_documents_render(self):
        for entry in docs.catalog():
            with self.subTest(document=entry['id']):
                self.assertTrue(docs.document(entry['id'], self.state)['html'])

    def test_linked_package_document_is_rejected(self):
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaises(ValueError):
                docs.document('guide-overview', self.state)

    def test_http_requires_token_and_rejects_replaced_run(self):
        current = copy.deepcopy(self.state)
        with patch.object(dashboard, 'status', side_effect=lambda root: current):
            server, url = dashboard.create_server(Path.cwd())
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for endpoint in ('documents', 'document/task-contract', 'document/guide-overview', 'documents.js'):
                    with urllib.request.urlopen(url + endpoint) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers['Cache-Control'], 'no-store')
                for endpoint in ('document/../.env', 'document/%2e%2e%2f.env'):
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(url + endpoint)
                    self.assertEqual(caught.exception.code, 404)
                    caught.exception.close()
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/wrong/documents')
                self.assertEqual(caught.exception.code, 404)
                caught.exception.close()
                current['run_id'] = 'replacement'
                for endpoint in ('documents', 'document/task-contract'):
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(url + endpoint)
                    self.assertEqual(caught.exception.code, 410)
                    caught.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)
