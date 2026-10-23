"""Codex boundary regressions; all owner identities/storage are disposable fixtures."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import codex_hook
import codex_compat
import delivery
import ownership
import safety


class CodexCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.base / 'task'
        self.root.mkdir()
        self.enterContext(patch.object(ownership, 'REGISTRY', None))
        self.enterContext(patch.dict(os.environ, {'VEERA_HOST': 'codex', 'CLAUDE_PLUGIN_DATA': str(self.base / 'data')}))
        delivery.atomic(delivery.storage(self.root) / 'workspace.json', {'id': 'fixture', 'session_id': 'fixture-owner'})
        self.capability = ownership.enroll('fixture-owner', self.root, 'fixture')
        self.enterContext(patch.object(safety, 'status', return_value={'status': 'active', 'contract': {'scope': ['.codex/', '.CODEX/', '.GIT/', 'app.py']}}))
        (self.root / '.veera/state.json').write_text('{}')

    def request(self, tool, args):
        return codex_hook.handle({'hook_event_name': 'PreToolUse', 'session_id': 'fixture-owner',
                                  'cwd': str(self.root), 'tool_name': tool, 'tool_input': args})

    def test_import_does_not_change_host_namespace(self):
        with patch.dict(os.environ, {'VEERA_HOST': 'claude'}):
            importlib.reload(codex_hook)
            self.assertEqual(os.environ['VEERA_HOST'], 'claude')

    def test_codex_configuration_is_protected_even_if_in_scope(self):
        for path in ('.codex/config.toml', '.CODEX/config.toml', '.GIT/config'):
            with self.subTest(path=path):
                result = self.request('apply_patch', {'command': f'*** Begin Patch\n*** Add File: {path}\n+x\n*** End Patch'})
                self.assertEqual(result.get('hookSpecificOutput', {}).get('permissionDecision'), 'deny')

    def test_installed_adapter_instructions_can_be_read(self):
        for path in ('adapters/codex/README.md', 'adapters/codex/skills/fix/SKILL.md'):
            with self.subTest(path=path):
                self.assertEqual(self.request('Read', {'file_path': str(ROOT / path)}), {})
        self.assertEqual(self.request('Read', {'file_path': str(self.base / 'foreign.txt')})['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_authorized_controller_operations_and_shell_use_native_policy(self):
        before = Path(self.capability).read_bytes()
        script = (ROOT / 'scripts/delivery.py').as_posix()
        for operation in ('amend', 'resume', 'blocker-human-resolve'):
            command = f'python3 "{script}" {operation} --root "{self.root.as_posix()}" --file approval.json'
            for tool, args in (('Bash', {'command': command}), ('exec_command', {'cmd': command}), ('shell_command', {'command': command})):
                with self.subTest(operation=operation, tool=tool):
                    self.assertEqual(self.request(tool, args), {})
        for command in ('git status', 'echo one; echo two', 'python scripts/model_router.py --plan'):
            self.assertEqual(self.request('Bash', {'command': command}), {})
        self.assertEqual(Path(self.capability).read_bytes(), before)

    def test_patch_ask_is_converted_to_deny_too(self):
        with patch.object(safety, 'handle', return_value={'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'ask', 'permissionDecisionReason': 'approval needed'}}):
            result = self.request('apply_patch', {'command': '*** Begin Patch\n*** Add File: app.py\n+x\n*** End Patch'})
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_other_native_tools_are_not_blocked_just_for_their_name(self):
        for tool in ('functions.exec', 'write_stdin', 'mcp__files__write'):
            self.assertEqual(self.request(tool, {}), {})

    def test_terminal_task_cannot_mutate_but_can_use_recorded_recovery(self):
        with patch.object(safety, 'status', return_value={'status': 'blocked', 'contract': {'scope': []}}):
            for tool, args in (('Bash', {'command': 'echo one; echo two'}), ('functions.exec', {})):
                self.assertEqual(self.request(tool, args)['hookSpecificOutput']['permissionDecision'], 'deny')
            for interpreter in ('python3', '"' + Path(sys.executable).as_posix() + '"'):
                command = f'{interpreter} "{(ROOT / "scripts/delivery.py").as_posix()}" resume --root "{self.root.as_posix()}" --file approval.json'
                self.assertEqual(self.request('Bash', {'command': command}), {})
                self.assertEqual(self.request('Bash', {'command': command + '; echo extra'})['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_real_hook_child_uses_codex_namespace_and_keeps_denial(self):
        before = Path(self.capability).read_bytes()
        payload = {'hook_event_name': 'PreToolUse', 'session_id': 'fixture-owner',
                   'cwd': str(self.root), 'tool_name': 'Bash', 'tool_input': {'command': 'echo fixture'}}
        # This is only a hook evaluation; the command is never executed.
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/codex_hook.py')],
                                input=json.dumps(payload), text=True, capture_output=True,
                                env=dict(os.environ, VEERA_HOST='claude'), timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertEqual(Path(self.capability).read_bytes(), before)

    def test_real_bootstrap_discloses_limits_without_enrollment(self):
        data = self.base / 'bootstrap-data'
        payload = {'hook_event_name': 'UserPromptSubmit', 'session_id': 'fixture-bootstrap',
                   'cwd': str(self.root), 'prompt': '$veera:start'}
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/codex_hook.py')],
                                input=json.dumps(payload), text=True, capture_output=True,
                                env=dict(os.environ, CLAUDE_PLUGIN_DATA=str(data)), timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        context = json.loads(json.loads(result.stdout)['hookSpecificOutput']['additionalContext'].split('\n', 1)[1])
        self.assertFalse(context['veera_bootstrap']['enrolled'])
        self.assertFalse(context['veera_capabilities']['hook_ask'])
        self.assertEqual(context['veera_capabilities']['authority_recovery']['amend'], 'controller-validated')
        self.assertFalse(context['veera_capabilities']['extra_approval_gate'])
        self.assertFalse(data.exists())

    def test_diagnostics_do_not_require_or_read_ownership(self):
        before = Path(self.capability).read_bytes()
        with patch.object(ownership, 'lookup', side_effect=AssertionError('No ownership lookup')), patch.object(subprocess, 'run', side_effect=AssertionError('No child process')):
            report = codex_compat.diagnose(ROOT)
        self.assertEqual(report['package_status'], 'files-present')
        self.assertEqual(report['activation'], 'not-verified')
        self.assertEqual(report['errors'], [])
        self.assertEqual(Path(self.capability).read_bytes(), before)

    def test_diagnostic_cli_runs_without_bootstrap_or_writes(self):
        env = dict(os.environ)
        for key in ('VEERA_HOST', 'CLAUDE_PLUGIN_DATA', 'PLUGIN_DATA'):
            env.pop(key, None)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/codex_compat.py')],
                                cwd=self.root, env=env, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['activation'], 'not-verified')
        self.assertEqual(set(path.name for path in self.root.iterdir()), {'.veera'})

    def test_missing_or_malformed_package_is_diagnosed(self):
        root = self.base / 'broken-package'
        root.mkdir()
        self.assertEqual(codex_compat.diagnose(root)['package_status'], 'invalid')
        (root / '.codex-plugin').mkdir()
        manifest = root / '.codex-plugin/plugin.json'
        for invalid in ('{invalid', '[]', 'null'):
            manifest.write_text(invalid)
            self.assertEqual(codex_compat.diagnose(root)['package_status'], 'invalid')

    def test_valid_patches_remain_scoped_and_moves_check_both_paths(self):
        self.assertEqual(self.request('apply_patch', {'command': '*** Begin Patch\n*** Add File: app.py\n+x\n*** End Patch'}), {})
        for body in ('*** Add File: ../escape.py\n+x',
                     '*** Update File: app.py\n*** Move to: ../escape.py\n@@\n-x\n+y',
                     '*** Delete File: ../escape.py',
                     '*** Add File: app.py\n+x\n*** Add File: .codex/config.toml\n+y'):
            result = self.request('apply_patch', {'command': '*** Begin Patch\n' + body + '\n*** End Patch'})
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')


if __name__ == '__main__':
    unittest.main()
