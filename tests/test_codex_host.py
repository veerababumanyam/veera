"""Native metadata diagnostics must not invent trust or change host settings."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import codex_host


class CodexHostTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.hooks = [{'pluginId': codex_host.PLUGIN, 'eventName': event, 'enabled': True,
                       'trustStatus': 'trusted', 'sourcePath': str(self.root / 'adapters/codex/hooks.json')}
                      for event in ('preToolUse', 'userPromptSubmit')]

    def result(self, hooks=None):
        return {'result': {'data': [{'hooks': self.hooks if hooks is None else hooks, 'errors': [], 'warnings': []}]}}

    def test_trusted_disabled_modified_missing_and_package_mismatch(self):
        self.assertEqual(codex_host.summarize(self.result(), self.root)['status'], 'ready')
        for changes, expected in (({'enabled': False}, 'disabled'), ({'trustStatus': 'modified'}, 'review-required'),
                                  ({'trustStatus': None}, 'review-required'), ({'sourcePath': str(self.root / 'old/hooks.json')}, 'package-mismatch')):
            hooks = copy.deepcopy(self.hooks)
            hooks[0].update(changes)
            with self.subTest(expected=expected):
                self.assertEqual(codex_host.summarize(self.result(hooks), self.root)['status'], expected)
        self.assertEqual(codex_host.summarize(self.result(self.hooks[:1]), self.root)['status'], 'missing')

    def test_foreign_plugin_metadata_is_not_returned(self):
        hooks = [*self.hooks, {'pluginId': 'foreign', 'secret': 'must-not-return'}]
        result = codex_host.summarize(self.result(hooks), self.root)
        self.assertEqual(len(result['hooks']), 2)
        self.assertNotIn('must-not-return', json.dumps(result))
        self.assertFalse(result['trust_changed'])

    def test_rejected_or_malformed_response_cannot_claim_ready(self):
        for value in (None, {}, {'error': {'message': 'Denied'}}, {'result': {'data': []}},
                      {'result': {'data': [{'hooks': None}]}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                codex_host.summarize(value, self.root)

    def test_unavailable_cli_or_cwd_reports_unknown_trust(self):
        with patch('model_router.find_codex', return_value=None):
            self.assertEqual(codex_host.inspect(self.root, self.root)['status'], 'unavailable')
        result = codex_host.inspect(self.root, self.root / 'absent', executable=sys.executable)
        self.assertEqual(result['status'], 'unavailable')
        self.assertFalse(result['trust_changed'])

    def test_transport_only_initializes_and_lists_hooks(self):
        script = self.root / 'metadata_fixture.py'
        log = self.root / 'requests.jsonl'
        script.write_text('import sys,json\nfrom pathlib import Path\n'
                          f'log=Path({str(log)!r})\n'
                          'for line in sys.stdin:\n'
                          ' item=json.loads(line)\n'
                          ' with log.open("a") as stream: stream.write(line)\n'
                          ' if item.get("id")==1: print(json.dumps({"id":1,"result":{}}),flush=True)\n'
                          f' if item.get("id")==2: print(json.dumps({{**{self.result()!r},"id":2}}),flush=True)\n', encoding='utf-8')
        launch = subprocess.Popen
        children = []

        def fake(argv, **kwargs):
            self.assertEqual(argv[1:], ['--no-daemon', 'app-server', '--stdio'])
            child = launch([sys.executable, str(script)], **kwargs)
            children.append(child)
            return child

        with patch.object(codex_host.subprocess, 'Popen', side_effect=fake):
            result = codex_host.inspect(self.root, self.root, executable='fixture-only')
        self.assertEqual(result['status'], 'ready')
        requests = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual([item['method'] for item in requests], ['initialize', 'initialized', 'hooks/list'])
        self.assertEqual(requests[-1]['params']['cwds'], [str(self.root)])
        self.assertIsNotNone(children[0].poll())

    def test_timeout_stops_only_own_diagnostic_child(self):
        launch = subprocess.Popen
        children = []

        def fake(argv, **kwargs):
            child = launch([sys.executable, '-c', 'import time; time.sleep(30)'], **kwargs)
            children.append(child)
            return child

        with patch.object(codex_host.subprocess, 'Popen', side_effect=fake):
            result = codex_host.inspect(self.root, self.root, executable='fixture-only', timeout=.05)
        self.assertEqual(result['status'], 'unavailable')
        self.assertIsNotNone(children[0].poll())
