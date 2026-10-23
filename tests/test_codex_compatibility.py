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

    def detached_request(self, tool, args):
        return codex_hook.handle({'hook_event_name': 'PreToolUse', 'session_id': 'fixture-owner',
                                  'cwd': str(self.base / 'chat'), 'tool_name': tool, 'tool_input': args})

    def test_canonical_bash_session_cwd_is_not_execution_cwd(self):
        # Native Codex drops exec_command.workdir from the canonical Bash event.
        # Do not misrepresent session cwd as an execution boundary or parse cd.
        self.assertEqual(self.detached_request('Bash', {'command': 'git status --short'}), {})
        self.assertEqual(self.detached_request('spawn_agent', {'message': 'Read-only review of the task'}), {})
        with patch.object(safety, 'status', return_value={'status': 'blocked'}):
            for tool, args in [('Bash', {'command': 'git status'}), ('spawn_agent', {'message': 'review'})]:
                self.assertEqual(self.detached_request(tool, args)['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_explicit_execution_workdir_is_checked_when_exposed(self):
        for tool, command_key in [('exec_command', 'cmd'), ('shell_command', 'command')]:
            with self.subTest(tool=tool):
                self.assertEqual(self.detached_request(tool, {command_key: 'git status', 'workdir': str(self.root)}), {})
                for directory in (str(self.base), str(self.base / 'foreign'), 17, ''):
                    result = self.detached_request(tool, {command_key: 'git status', 'workdir': directory})
                    self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')
                self.assertEqual(self.detached_request(tool, {command_key: 'git status'})['hookSpecificOutput']['permissionDecision'], 'deny')
        nested = self.root / 'nested'
        (nested / '.git').mkdir(parents=True)
        result = self.detached_request('exec_command', {'cmd': 'git status', 'workdir': str(nested)})
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_detached_chat_absolute_patch_targets_keep_scope(self):
        for target, permitted in [(self.root / 'app.py', True), (self.root / 'outside.py', False),
                                  (self.root / '.codex/config.toml', False), (self.base / 'foreign.py', False),
                                  (Path('app.py'), False)]:
            patch_text = f'*** Begin Patch\n*** Add File: {target.as_posix()}\n+x\n*** End Patch'
            result = self.detached_request('apply_patch', {'command': patch_text})
            with self.subTest(target=str(target)):
                self.assertEqual(result == {}, permitted)
        nested = self.root / 'nested'
        (nested / '.git').mkdir(parents=True)
        result = self.detached_request('apply_patch', {'command': f'*** Begin Patch\n*** Add File: {(nested / "app.py").as_posix()}\n+x\n*** End Patch'})
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_detached_chat_reads_still_check_exact_targets(self):
        for target, permitted in [(self.root / 'app.py', True), (ROOT / 'docs/agent-contract.md', True),
                                  (self.base / 'foreign.py', False), (Path('app.py'), False)]:
            with self.subTest(target=str(target)):
                self.assertEqual(self.detached_request('Read', {'file_path': str(target)}) == {}, permitted)

    def test_detached_chat_does_not_skip_owner_validation(self):
        (self.root / '.veera/workspace.json').write_text(json.dumps({'id': 'other', 'session_id': 'fixture-owner'}))
        for tool, args in [('Bash', {'command': 'git status'}), ('spawn_agent', {'message': 'review'})]:
            self.assertEqual(self.detached_request(tool, args)['hookSpecificOutput']['permissionDecision'], 'deny')

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
        for operation in ('amend', 'resume', 'extend-repairs', 'blocker-human-resolve'):
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

    def test_exhausted_recovery_inspection_and_chat_handoff(self):
        before = Path(self.capability).read_bytes()
        with patch.object(safety, 'status', return_value={'status': 'budget-exhausted'}):
            for tool, args in [
                ('read_file', {'path': str(self.root / 'app.py')}),
                ('Bash', {'command': f'Get-Content -LiteralPath "{self.root / "app.py"}"'}),
                ('Bash', {'command': f'git -C "{self.root}" status --short'}),
                ('mcp__codex_app__read_thread', {'threadId': 'recorded-task-chat'}),
                ('mcp__codex_app__send_message_to_thread', {'threadId': 'recorded-task-chat', 'prompt': 'Checkpoint handoff'}),
            ]:
                with self.subTest(tool=tool, args=args):
                    self.assertEqual(self.request(tool, args), {})
        self.assertEqual(Path(self.capability).read_bytes(), before)

    @unittest.skipUnless(os.name == 'nt', 'PowerShell call operator is Windows-only')
    def test_windows_controller_call_operator_recovery(self):
        command = (f'& "{Path(sys.executable).as_posix()}" "{(ROOT / "scripts/delivery.py").as_posix()}" status '
                   f'--root "{self.root}" --session-id fixture-owner --capability-file "{self.capability}"')
        with patch.object(safety, 'status', return_value={'status': 'budget-exhausted'}):
            self.assertEqual(self.request('Bash', {'command': command}), {})
            for bad in (command + '; echo extra', command + ' | cat', command + ' > state.json',
                        command.replace('fixture-owner', 'foreign-owner'),
                        command.replace(str(self.root), str(self.base / 'foreign'))):
                self.assertEqual(self.request('Bash', {'command': bad})['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_exhausted_recovery_does_not_open_arbitrary_execution(self):
        with patch.object(safety, 'status', return_value={'status': 'budget-exhausted'}):
            for tool, args in [
                ('read_file', {'path': str(self.base / 'foreign.txt')}),
                ('Bash', {'command': f'Get-Content -LiteralPath "{self.base / "foreign.txt"}"'}),
                ('Bash', {'command': f'Get-Content -LiteralPath "{self.root / "app.py"}"; echo extra'}),
                ('Bash', {'command': f'git -C "{self.root}" reset --hard'}),
                ('functions.exec', {'code': 'arbitrary()'}),
                ('mcp__codex_app__handoff_thread', {'threadId': 'other'}),
                ('mcp__unknown__read', {}),
                ('Write', {'file_path': str(self.root / 'app.py')}),
            ]:
                with self.subTest(tool=tool, args=args):
                    self.assertEqual(self.request(tool, args)['hookSpecificOutput']['permissionDecision'], 'deny')
        (self.root / '.veera/workspace.json').write_text(json.dumps({'id': 'foreign', 'session_id': 'fixture-owner'}))
        self.assertEqual(self.request('mcp__codex_app__read_thread', {'threadId': 'recorded-task-chat'})['hookSpecificOutput']['permissionDecision'], 'deny')

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

    def test_stopped_controller_can_receive_exact_bootstrap_environment(self):
        base = (f'"{Path(sys.executable)}" "{ROOT / "scripts/delivery.py"}" status '
                f'--root "{self.root}" --session-id fixture-owner --capability-file "{self.capability}"')
        flags = f' --host codex --plugin-data "{self.base / "data"}"'
        with patch.object(safety, 'status', return_value={'status': 'budget-exhausted'}):
            self.assertEqual(self.request('Bash', {'command': base + flags}), {})
            for invalid in (flags.replace('codex', 'claude'), flags.replace(str(self.base / 'data'), str(self.base / 'foreign')),
                            flags + ' --host codex', flags + '; echo extra'):
                self.assertEqual(self.request('Bash', {'command': base + invalid})['hookSpecificOutput']['permissionDecision'], 'deny')
            self.assertEqual(self.request('Bash', {'command': f'Get-Content -LiteralPath "{ROOT / "README.md"}"'}), {})
            self.assertEqual(self.request('apply_patch', {'command': f'*** Begin Patch\n*** Add File: {(self.root / ".veera-artifacts/resume.json").as_posix()}\n+{{}}\n*** End Patch'}), {})

    def test_stopped_chat_discovery_preserves_owner_and_execution_boundaries(self):
        owner_before = Path(self.capability).read_bytes()
        state_before = (self.root / '.veera/state.json').read_bytes()
        for status in safety.TERMINAL:
            with self.subTest(status=status), patch.object(safety, 'status', return_value={'status': status}):
                for tool in ('mcp__codex_app__list_threads', 'mcp__codex_app__list_projects'):
                    self.assertEqual(self.detached_request(tool, {}), {})
                for tool in ('mcp__codex_app__create_thread', 'mcp__codex_app__handoff_thread',
                             'mcp__codex_app__unknown', 'ListAgents', 'functions.exec'):
                    self.assertEqual(self.detached_request(tool, {})['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertEqual(Path(self.capability).read_bytes(), owner_before)
        self.assertEqual((self.root / '.veera/state.json').read_bytes(), state_before)
        (self.root / '.veera/workspace.json').write_text(json.dumps({'id': 'foreign', 'session_id': 'fixture-owner'}))
        for tool in ('mcp__codex_app__list_threads', 'mcp__codex_app__list_projects'):
            self.assertEqual(self.detached_request(tool, {})['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_controller_bootstrap_options_work_without_inherited_environment(self):
        state = {'status': 'budget-exhausted', 'contract': {}, 'contract_hash': delivery.digest({})}
        (self.root / '.veera/state.json').write_text(json.dumps(state))
        before = Path(self.capability).read_bytes()
        env = dict(os.environ)
        env.pop('VEERA_HOST', None)
        env.pop('CLAUDE_PLUGIN_DATA', None)
        args = [sys.executable, str(ROOT / 'scripts/delivery.py'), 'status', '--root', str(self.root),
                '--session-id', 'fixture-owner', '--capability-file', self.capability,
                '--host', 'codex', '--plugin-data', str(self.base / 'data')]
        result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'budget-exhausted')
        for bad_env in (dict(env, VEERA_HOST='claude'), dict(env, CLAUDE_PLUGIN_DATA=str(self.base / 'foreign'))):
            denied = subprocess.run(args, env=bad_env, capture_output=True, text=True, timeout=10)
            self.assertEqual(denied.returncode, 2)
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
