"""Automatic context delivery; task intent is decided by the coordinator."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bootstrap
import codex_hook
import ownership
import safety

ROOT = Path(bootstrap.__file__).resolve().parents[1]


class AutoEntryTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch.object(ownership, 'REGISTRY', None))
        self.enterContext(patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA': self.directory}))

    def payload(self, prompt):
        return {'hook_event_name': 'UserPromptSubmit', 'session_id': 'auto-entry-fixture',
                'cwd': self.directory, 'prompt': prompt}

    def context(self, result):
        return json.loads(result['hookSpecificOutput']['additionalContext'].split('\n', 1)[1])

    def test_natural_requests_and_followups_receive_identity_without_commands(self):
        for host in ('codex', 'claude'):
            with patch.dict(os.environ, {'VEERA_HOST': host}):
                for prompt in ('Add CSV export to the reports page.', 'The total is wrong for refunds.',
                               'Can you fix the login crash?', 'Please continue with the agreed plan.',
                               '修复登录页面的错误', 'Make it work', 'I need a dark mode toggle.'):
                    with self.subTest(host=host, prompt=prompt):
                        data = self.context(bootstrap.handle(self.payload(prompt), host))
                        self.assertEqual(data['veera_bootstrap']['requested_action'], 'auto')
                        self.assertEqual(data['veera_bootstrap']['session_id'], 'auto-entry-fixture')
                        self.assertEqual(data['veera_bootstrap']['host'], host)
                        self.assertEqual(data['veera_bootstrap']['activation'], 'automatic')
                        self.assertFalse(data['veera_bootstrap']['enrolled'])
                        self.assertTrue(Path(data['veera_bootstrap']['routing_guide']).is_file())
        self.assertEqual(list(Path(self.directory).iterdir()), [])

    def test_context_is_not_a_classification_or_enrollment_for_questions_or_optouts(self):
        for prompt in ('What does this function do?', 'Do not use Veera; just explain the error.',
                       'Explain why someone wrote "fix this bug".', 'hello'):
            data = self.context(bootstrap.handle(self.payload(prompt), 'codex'))
            self.assertEqual(data['veera_bootstrap']['requested_action'], 'auto')
            self.assertFalse(data['veera_bootstrap']['enrolled'])
        self.assertEqual(list(Path(self.directory).iterdir()), [])

    def test_control_commands_and_invalid_payloads_do_not_start_automatic_routing(self):
        for host in ('codex', 'claude'):
            for prompt in ('', '  ', None, [], '/other:build x', '$veera:starter',
                           '[$other:build](C:/other/SKILL.md)', '> fix this', '```\nfix this\n```'):
                self.assertEqual(bootstrap.handle(self.payload(prompt), host), {})

    def test_automatic_context_cannot_invent_identity_or_use_parent_environment(self):
        payload = self.payload('Fix the test')
        payload.pop('session_id')
        with patch.dict(os.environ, {'CODEX_THREAD_ID': 'parent', 'CODEX_SESSION_ID': 'parent'}):
            output = bootstrap.handle(payload, 'codex')['hookSpecificOutput']['additionalContext']
            self.assertNotIn('veera_bootstrap', output)
            self.assertIn('unavailable', output)
        self.assertEqual(list(Path(self.directory).iterdir()), [])

    def test_skill_read_hook_provides_real_context_for_delegated_desktop_entry(self):
        for host, handler, prefix in [('codex', codex_hook.handle, 'adapters/codex/skills'),
                                      ('claude', safety.handle, 'skills')]:
            with patch.dict(os.environ, {'VEERA_HOST': host}):
                path = str(ROOT / prefix / 'build/SKILL.md')
                for tool, args in [('Read', {'file_path': path}),
                                   ('Bash', {'command': 'Get-Content -LiteralPath ' + repr(path)}),
                                   ('exec_command', {'cmd': 'cat "' + path.replace('\\', '/') + '"'})]:
                    payload = {'hook_event_name': 'PreToolUse', 'session_id': 'auto-entry-fixture',
                               'cwd': self.directory, 'tool_name': tool, 'tool_input': args}
                    result = handler(payload)
                    self.assertEqual(result['hookSpecificOutput']['hookEventName'], 'PreToolUse')
                    self.assertNotIn('permissionDecision', result['hookSpecificOutput'])
                    data = self.context(result)['veera_bootstrap']
                    self.assertEqual(data['requested_action'], 'auto')
                    self.assertEqual(data['identity_event'], 'PreToolUse')
                    self.assertEqual(data['session_id'], payload['session_id'])
                    self.assertFalse(data['enrolled'])
        self.assertEqual(list(Path(self.directory).iterdir()), [])

    def test_unrelated_tools_and_foreign_skill_paths_receive_no_fallback_context(self):
        for host, handler in [('codex', codex_hook.handle), ('claude', safety.handle)]:
            with patch.dict(os.environ, {'VEERA_HOST': host}):
                for args in ({'cmd': 'Get-Content C:/foreign/skills/build/SKILL.md'},
                             {'cmd': 'git status'}, {'cmd': 'echo "' + str(ROOT / 'skills/build/SKILL.md') + '"'}):
                    self.assertEqual(handler({'hook_event_name': 'PreToolUse', 'session_id': 'auto-entry-fixture',
                                              'tool_name': 'exec_command', 'tool_input': args}), {})

    def test_router_delegates_do_not_recursively_activate(self):
        with patch.dict(os.environ, {'VEERA_ROUTER_ACTIVE': '1'}):
            self.assertEqual(bootstrap.handle(self.payload('Fix the test'), 'codex'), {})

    def test_owned_denial_is_never_replaced_by_skill_read_context(self):
        for host, handler, prefix in [('codex', codex_hook.handle, 'adapters/codex/skills'),
                                      ('claude', safety.handle, 'skills')]:
            with patch.dict(os.environ, {'VEERA_HOST': host}):
                ownership.enroll('auto-entry-fixture', self.directory, 'fixture-workspace')
                payload = {'hook_event_name': 'PreToolUse', 'session_id': 'auto-entry-fixture',
                           'tool_name': 'Read', 'tool_input': {'file_path': str(ROOT / prefix / 'build/SKILL.md')}}
                with patch.object(safety, 'evaluate', return_value='Owned task denial'):
                    result = handler(payload)['hookSpecificOutput']
                self.assertEqual(result['permissionDecision'], 'deny')
                self.assertNotIn('additionalContext', result)
