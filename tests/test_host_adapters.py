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

    def test_task_entry_bootstraps_in_same_prompt_without_enrollment(self):
        for host, commands in [('claude', ['/veera:build Create a feature', '/veera:fix Repair the issue', '/veera:dashboard']),
                               ('codex', ['$veera:build Create a feature', '$veera-fix Repair the issue', '$veera:dashboard'])]:
            with patch.dict(os.environ, {'VEERA_HOST': host}):
                for prompt in commands:
                    with self.subTest(host=host, prompt=prompt):
                        result = bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': 'owner', 'cwd': str(self.root), 'prompt': prompt}, host)
                        data = json.loads(result['hookSpecificOutput']['additionalContext'].split('\n', 1)[1])['veera_bootstrap']
                        self.assertEqual(data['session_id'], 'owner')
                        self.assertEqual(data['host'], host)
                        self.assertIn(data['requested_action'], ('build', 'fix', 'dashboard'))
                        self.assertFalse(data['enrolled'])
        self.assertFalse(self.data.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_mentions_wrong_host_and_similar_commands_do_not_activate(self):
        for host in ('claude', 'codex'):
            for prompt in ('Explain /veera:fix', '`$veera:build`', '/veera:fixer thing', '$veera:build-more',
                           '/veera:route list files', '$veera:diagnose', '', None, ['/veera:fix']):
                self.assertEqual(bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': 'owner', 'prompt': prompt}, host), {})
        for host, prompt in [('claude', '$veera:fix issue'), ('codex', '/veera:fix issue')]:
            self.assertEqual(bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': 'owner', 'prompt': prompt}, host), {})

    def test_direct_task_still_requires_actual_host_identity_and_data(self):
        for session in (None, '../../invalid'):
            result = bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': session, 'prompt': '/veera:fix issue'})
            self.assertIn('BLOCKED', result['hookSpecificOutput']['additionalContext'])
        with patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA': ''}):
            result = bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': 'owner', 'prompt': '/veera:build feature'})
            self.assertIn('BLOCKED', result['hookSpecificOutput']['additionalContext'])
        self.assertFalse(self.data.exists())

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

    def test_cleanup_failure_preserves_success_without_repeating_publish(self):
        import git_delivery
        self.session_id, self.capability = 'owner', self.owner()
        from session_fixture import cli
        with patch.object(git_delivery, 'publish', return_value={'status': 'complete'}) as publish, patch.object(ownership, 'unbind', side_effect=OSError('fixture cleanup failure')):
            result = cli(self, 'publish', '--root', str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'complete')
        self.assertEqual(json.loads(result.stdout)['session_binding'], 'cleanup-required')
        publish.assert_called_once()
        self.assertTrue(Path(self.capability).exists())

    def test_incomplete_tasks_cannot_release_the_owner_binding(self):
        capability = self.owner()
        for state in ('active', 'ready', 'blocked', 'budget-exhausted', 'user-stopped'):
            with patch.object(d, 'status', return_value={'status': state}):
                with self.assertRaisesRegex(ValueError, 'completed'):
                    ownership.unbind('owner', self.root, capability)
            self.assertTrue(Path(capability).exists())


if __name__ == '__main__':
    unittest.main()
