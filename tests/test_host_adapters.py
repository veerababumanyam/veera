import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bootstrap
import delivery as d
import ownership
import safety


class HostAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.temp) / 'task'
        self.root.mkdir()
        self.data = Path(self.temp) / 'data'
        self.enterContext(patch.object(ownership, 'REGISTRY', None))
        self.enterContext(patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA': str(self.data), 'VEERA_HOST': 'claude'}))

    def owner(self):
        d.atomic(d.storage(self.root) / 'workspace.json', {'id': 'workspace1', 'session_id': 'owner'})
        return ownership.enroll('owner', self.root, 'workspace1')

    def test_explicit_bootstrap_only_no_writes(self):
        for prompt in ('hello', ' /veera:start', '/veera:start extra', 'please /veera:start', '"/veera:start"'):
            self.assertEqual(bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': 'owner', 'prompt': prompt}), {})
        result = bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': 'owner', 'prompt': '/veera:start'})
        self.assertIn('"session_id": "owner"', result['hookSpecificOutput']['additionalContext'])
        self.assertFalse(self.data.exists())

    def test_missing_persistent_data_blocks_enrollment_before_git(self):
        with patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA': ''}), patch.object(subprocess, 'run', side_effect=AssertionError('Git must not run')):
            with self.assertRaises(ValueError):
                ownership.enroll('owner', self.root, 'workspace1')
            result = bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': 'owner', 'prompt': '/veera:start'})
            self.assertIn('BLOCKED', result['hookSpecificOutput']['additionalContext'])

    def test_owner_failure_denies_unbound_failure_noop(self):
        for payload in ([], None, 'string', {'session_id': '../../bad'}, {'session_id': 'stranger'}):
            self.assertEqual(safety.handle(payload), {})
        self.owner()
        with patch.object(safety, 'evaluate', side_effect=RuntimeError('owned failure')):
            result = safety.handle({'session_id': 'owner'})
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')
        Path(ownership.registry() / (ownership.session_key('owner') + '.json')).write_text('invalid JSON')
        self.assertEqual(safety.handle({'session_id': 'owner'})['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_top_level_malformed_json_does_not_block_unknown_session(self):
        output = io.StringIO()
        with patch.object(sys, 'stdin', io.StringIO('{bad')), contextlib.redirect_stdout(output):
            safety.main()
        self.assertEqual(json.loads(output.getvalue()), {})

    def test_persistent_namespaces_and_migration(self):
        legacy = Path(self.temp) / 'legacy'
        legacy.mkdir()
        record = {'session_id': 'owner', 'root': str(self.root), 'workspace_id': 'workspace1', 'capability': 'fixture-only'}
        path = legacy / (ownership.session_key('owner') + '.json')
        path.write_text(json.dumps(record))
        d.atomic(d.storage(self.root) / 'workspace.json', {'id': 'workspace1', 'session_id': 'owner'})
        result = ownership.migrate('owner', self.root, path)
        self.assertTrue(path.exists())
        self.assertEqual(ownership.migrate('owner', self.root, path)['status'], 'already-migrated')
        self.assertEqual(ownership.authorize('owner', self.root, result['capability_file']), record)
        with patch.dict(os.environ, {'VEERA_HOST': 'codex'}):
            self.assertIsNone(ownership.lookup('owner'))
        with self.assertRaises(ValueError):
            ownership.migrate('foreign', self.root, path)

    def test_codex_exact_trigger_and_malformed_owner_input(self):
        import codex_hook
        with patch.dict(os.environ, {'VEERA_HOST': 'codex'}):
            for command, expected in (('$veera-start', True), ('/veera:start', False), ('$veera-start extra', False)):
                result = codex_hook.handle({'session_id': 'owner', 'hook_event_name': 'UserPromptSubmit', 'prompt': command})
                self.assertEqual(bool(result), expected)
            self.assertFalse(self.data.exists())
            for tool in ('exec_command', 'apply_patch'):
                self.assertEqual(codex_hook.handle({'session_id': 'unknown', 'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': None}), {})
            self.owner()
            for tool in ('exec_command', 'apply_patch'):
                for invalid in (None, [], 'invalid'):
                    result = codex_hook.handle({'session_id': 'owner', 'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': invalid})
                    self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_codex_never_emits_unsupported_ask(self):
        import codex_hook
        with patch.dict(os.environ, {'VEERA_HOST': 'codex'}):
            self.owner()
            with patch.object(safety, 'handle', return_value={'hookSpecificOutput': {'permissionDecision': 'ask', 'permissionDecisionReason': 'approval needed'}}):
                result = codex_hook.handle({'session_id': 'owner', 'hook_event_name': 'PreToolUse', 'tool_name': 'exec_command', 'tool_input': {'cmd': 'python3 app.py'}})
                self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')
            result = codex_hook.handle({'session_id': 'owner', 'hook_event_name': 'PreToolUse', 'tool_name': 'apply_patch', 'tool_input': {'command': '...'}})
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')


if __name__ == '__main__':
    unittest.main()
