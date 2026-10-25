"""Bound sessions whose host folder stays the original checkout keep working.

Desktop and delegated sessions cannot change their folder after `workspace`
binds them to the sibling task worktree. Disposable repos and an isolated
session registry only.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d
import git_delivery as g
import ownership
import safety


class SessionBindingTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(patch.object(ownership, 'REGISTRY', self.base / 'sessions'))
        self.original = self.base / 'repo'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.original)], check=True)
        g.git(self.original, 'config', 'user.email', 'fixture@example.invalid')
        g.git(self.original, 'config', 'user.name', 'Fixture')
        (self.original / 'app.py').write_text('value = 1\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-m', 'Fixture baseline')
        (self.base / 'foreign').mkdir()
        (self.base / 'foreign' / 'secret.txt').write_text('other project')
        self.session_id = 'fixture-desktop-owner'
        metadata = g.workspace(self.original, 'bound', self.session_id)
        self.root = Path(metadata['root'])
        self.capability = metadata['capability_file']
        contract = {'scope': ['app.py'], 'criteria': [{'id': 'C1', 'text': 'Test', 'checks': ['test']}], 'checks': [{'id': 'test', 'kind': 'static', 'argv': ['true']}]}
        d.init(self.root, 'fix', 'bound fixture', contract, 5)

    def hook(self, tool, tool_input=None, cwd=None, session_id=None):
        payload = {'session_id': session_id or self.session_id, 'cwd': str(cwd or self.original), 'tool_name': tool, 'tool_input': tool_input or {}}
        return safety.evaluate(payload)

    def anchored(self, command):
        return 'cd "' + str(self.root) + '" && ' + command

    def test_session_tools_work_from_original_checkout(self):
        for tool in ('ToolSearch', 'Agent', 'Skill', 'mcp__ccd_turn__update_plan', 'mcp__ccd_session__mark_chapter'):
            with self.subTest(tool=tool):
                self.assertIsNone(self.hook(tool))

    def test_reads_cover_worktree_and_original_only(self):
        self.assertIsNone(self.hook('Read', {'file_path': str(self.root / 'app.py')}))
        self.assertIsNone(self.hook('Read', {'file_path': str(self.original / 'app.py')}))
        self.assertIsNone(self.hook('Grep', {'pattern': 'value'}))  # Defaults to the original folder.
        self.assertIsNone(self.hook('Glob', {'pattern': '*.py', 'path': str(self.root)}))
        self.assertIn('outside this task', self.hook('Read', {'file_path': str(self.base / 'foreign' / 'secret.txt')}))

    def test_writes_land_only_in_task_worktree(self):
        self.assertIsNone(self.hook('Edit', {'file_path': str(self.root / 'app.py'), 'old_string': '1', 'new_string': '2'}))
        reason = self.hook('Edit', {'file_path': str(self.original / 'app.py'), 'old_string': '1', 'new_string': '2'})
        self.assertIn('original checkout', reason)
        self.assertIn(str(self.root / 'app.py'), reason)
        self.assertIn('frozen scope', self.hook('Write', {'file_path': str(self.root / 'other.py'), 'content': ''}))
        self.assertIn('outside the authorized', self.hook('Write', {'file_path': str(self.base / 'foreign' / 'x.py'), 'content': ''}))

    def test_anchored_commands_run_and_test_in_worktree(self):
        allowed = [('Bash', self.anchored('python -m unittest -q')),
                   ('Bash', self.anchored('python -m pytest tests/test_app.py -x 2>&1 | tail -20')),
                   ('Bash', self.anchored('python -m pytest tests/test_delivery.py::TestA -k "a and not b"')),
                   ('Bash', self.anchored('git diff --stat HEAD~1..HEAD')),
                   ('Bash', 'git -C "' + str(self.root) + '" status --short'),
                   ('PowerShell', 'Set-Location -LiteralPath "' + str(self.root) + '"; python -m pytest -q'),
                   ('PowerShell', 'cd "' + str(self.root) + '"; git add app.py')]
        for tool, command in allowed:
            with self.subTest(command=command):
                self.assertIsNone(self.hook(tool, {'command': command}))

    def test_unanchored_or_escaping_commands_refused_without_asking(self):
        refused = [('Bash', 'python -m pytest'),
                   ('Bash', 'cd "' + str(self.original) + '" && python -m pytest'),
                   ('Bash', 'cd "' + str(self.base / 'foreign') + '" && ls'),
                   ('Bash', self.anchored('cat ../foreign/secret.txt')),
                   ('Bash', self.anchored('cp app.py "' + str(self.original / 'app.py') + '"')),
                   ('Bash', self.anchored('python -c "print(1)"')),
                   ('Bash', self.anchored('bash -c "ls /"')),
                   ('Bash', 'cd repo-bound && python -m pytest'),  # Relative anchors resolve from the original.
                   ('Bash', self.anchored('X=1 python -c "print(1)"')),
                   ('Bash', self.anchored('ls && cat "' + str(self.base / 'foreign' / 'secret.txt') + '"')),
                   ('Bash', self.anchored('ls && cd "' + str(self.original) + '" && python -m pytest')),
                   ('Bash', self.anchored('docker run -v /:/host image')),
                   ('Bash', self.anchored('ls & python -m pytest')),
                   ('Bash', self.anchored('git push origin main')),
                   ('Bash', self.anchored('git worktree remove x')),
                   ('Bash', self.anchored('ls; rm -rf /')),
                   ('Bash', self.anchored('ls | tee out.txt')),
                   ('Bash', self.anchored('echo $(whoami)')),
                   ('Bash', self.anchored('pytest --rootdir=' + str(self.original))),
                   ('PowerShell', 'Remove-Item app.py'),
                   ('PowerShell', 'Set-Location "' + str(self.root) + '"; Remove-Item "' + str(self.base / 'foreign') + '"; Get-Item y')]
        for tool, command in refused:
            with self.subTest(command=command):
                reason = self.hook(tool, {'command': command})
                self.assertIsNotNone(reason)
                self.assertFalse(reason.startswith('ASK:'), 'Unattended sessions need an actionable refusal')

    def test_redirect_names_anchor_form(self):
        reason = self.hook('Bash', {'command': 'python -m pytest'})
        self.assertIn('cd "' + str(self.root) + '"', reason)

    def test_controller_still_reachable_and_authority_still_asks(self):
        script = str(Path(d.__file__).resolve())
        owner = f'--session-id {self.session_id} --capability-file {self.capability}'
        status = f'python3 {script} status --root {self.root} {owner}'
        self.assertIsNone(self.hook('Bash', {'command': status}))
        resume = f'python3 {script} resume --root {self.root} {owner} --file {self.root / "approval.json"}'
        self.assertTrue(self.hook('Bash', {'command': resume}).startswith('ASK:'))
        # Anchoring cannot launder an authority-sensitive controller call.
        self.assertIsNotNone(self.hook('Bash', {'command': self.anchored(resume)}))

    def test_other_projects_and_nested_repositories_still_refused(self):
        nested = self.original / 'vendor'
        nested.mkdir()
        (nested / '.git').mkdir()
        for cwd in (self.base / 'foreign', nested, self.base):
            with self.subTest(cwd=str(cwd)):
                self.assertIn('bound to its task worktree', self.hook('Read', {'file_path': str(self.root / 'app.py')}, cwd=cwd))
        self.assertIn('outside this task', self.hook('Read', {'file_path': str(nested / 'x.py')}))

    def test_terminal_run_refuses_anchored_execution(self):
        d.stop(self.root, 'stop')
        self.assertIn('no further', self.hook('Bash', {'command': self.anchored('python -m pytest')}))
        self.assertIn('no further', self.hook('PowerShell', {'command': 'cd "' + str(self.root) + '"; python -m pytest'}))

    def test_in_root_sessions_keep_approval_for_unanchored_shell(self):
        self.assertTrue(self.hook('Bash', {'command': 'python3 other.py'}, cwd=self.root).startswith('ASK:'))
        self.assertIsNone(self.hook('Bash', {'command': self.anchored('python -m pytest -q')}, cwd=self.root))

    def test_unbound_session_stays_no_op(self):
        with patch.object(safety, 'status', side_effect=AssertionError('unowned state read')):
            self.assertIsNone(self.hook('Bash', {'command': 'git push'}, session_id='unrelated-session'))

    def test_forged_original_in_another_owner_is_ignored(self):
        # The origin comes only from this owner's validated metadata.
        metadata = d.read_json(self.root / '.veera/workspace.json')
        metadata['id'] = 'f' * 32
        d.atomic(self.root / '.veera/workspace.json', metadata)
        self.assertIn('bound to its task worktree', self.hook('Read', {'file_path': str(self.root / 'app.py')}))

    def controller(self, operation, extra=''):
        script = str(Path(d.__file__).resolve())
        return (f'python3 "{script}" {operation} --root "{self.root}" --session-id {self.session_id} '
                f'--capability-file "{self.capability}"' + extra)

    def test_init_runs_with_host_identity_from_original_checkout(self):
        data = str(self.base / 'plugin-data')
        contract = self.root / '.veera-artifacts' / 'contract.json'
        init = self.controller('init', f' --mode fix --request fix --contract "{contract}" --minutes 30 --hard-minutes 60')
        forms = [('Bash', f'CLAUDE_PLUGIN_DATA="{data}" VEERA_HOST=claude {init}'),
                 ('Bash', f'env CLAUDE_PLUGIN_DATA="{data}" VEERA_HOST=claude {init}'),
                 ('Bash', f'export CLAUDE_PLUGIN_DATA="{data}" VEERA_HOST=claude && {init}'),
                 ('Bash', self.anchored(f'CLAUDE_PLUGIN_DATA="{data}" VEERA_HOST=claude {init}')),
                 ('Bash', f'CLAUDE_PLUGIN_DATA={data} {self.controller("check", " --id test")}'),
                 ('PowerShell', f"$env:CLAUDE_PLUGIN_DATA = '{data}'; $env:VEERA_HOST = 'claude'; {init}"),
                 ('PowerShell', 'Set-Location -LiteralPath "' + str(self.root) + f'"; $env:CLAUDE_PLUGIN_DATA = "{data}"; {init}')]
        with patch.dict('os.environ', {'CLAUDE_PLUGIN_DATA': data}):
            for tool, command in forms:
                with self.subTest(command=command):
                    self.assertIsNone(self.hook(tool, {'command': command}))
            # The wrapper adds no authority: another identity or variable is refused.
            other = str(self.base / 'other-data')
            self.assertIn('identity does not match', self.hook('Bash', {'command': f'CLAUDE_PLUGIN_DATA="{other}" {init}'}))
            self.assertIn('identity does not match', self.hook('Bash', {'command': f'VEERA_HOST=codex {init}'}))
            self.assertIn('Duplicate owner options', self.hook('Bash', {'command': f'CLAUDE_PLUGIN_DATA="{data}" {init} --session-id other'}))
            foreign = init.replace(self.session_id, 'another-session')
            self.assertIn('identity does not match', self.hook('Bash', {'command': f'CLAUDE_PLUGIN_DATA="{data}" {foreign}'}))
            for command in (f'PYTHONPATH=x {init}', f'CLAUDE_PLUGIN_DATA="{data}" {init} && ls',
                            'cd "' + str(self.original) + f'" && CLAUDE_PLUGIN_DATA="{data}" {init}'):
                with self.subTest(command=command):
                    self.assertIn('shell starts in the original checkout', self.hook('Bash', {'command': command}))
            # Authority-sensitive calls still ask, on either shell and under any wrapper.
            resume = self.controller('resume', f' --file "{self.root / "approval.json"}"')
            for tool, command in (('Bash', f'CLAUDE_PLUGIN_DATA="{data}" {resume}'), ('PowerShell', f"$env:CLAUDE_PLUGIN_DATA = '{data}'; {resume}"),
                                  ('Bash', self.anchored(f'VEERA_HOST=claude {resume}'))):
                with self.subTest(command=command):
                    self.assertTrue(self.hook(tool, {'command': command}).startswith('ASK:'))

    def test_relative_controller_inputs_resolve_in_the_worktree(self):
        data = str(self.base / 'plugin-data')
        init = self.controller('init', ' --mode fix --request fix --contract .veera-artifacts/contract.json --minutes 30 --hard-minutes 60')
        review = self.controller('review', ' --file=.veera-artifacts/review.json')
        with patch.dict('os.environ', {'CLAUDE_PLUGIN_DATA': data}):
            # From the original checkout the shell would read the original's file.
            for command, flag, name in ((f'CLAUDE_PLUGIN_DATA="{data}" {init}', '--contract', 'contract.json'),
                                        (f'CLAUDE_PLUGIN_DATA="{data}" {review}', '--file', 'review.json')):
                with self.subTest(command=command):
                    reason = self.hook('Bash', {'command': command})
                    self.assertIn(flag + ' "' + str(self.root / '.veera-artifacts' / name) + '"', reason)
                    self.assertIn('cd "' + str(self.root) + '"', reason)
            self.assertIsNone(self.hook('Bash', {'command': self.anchored(f'CLAUDE_PLUGIN_DATA="{data}" {init}')}))
            # A session already working in the worktree resolves relative inputs there.
            self.assertIsNone(self.hook('Bash', {'command': f'CLAUDE_PLUGIN_DATA="{data}" {init}'}, cwd=self.root))

    def test_source_edits_before_init_name_the_next_step(self):
        metadata = g.workspace(self.original, 'draft', 'fixture-draft-owner')
        root = Path(metadata['root'])
        payload = {'session_id': 'fixture-draft-owner', 'cwd': str(self.original), 'tool_name': 'Edit',
                   'tool_input': {'file_path': str(root / 'app.py'), 'old_string': '1', 'new_string': '2'}}
        reason = safety.evaluate(payload)
        self.assertIn('after init', reason)
        self.assertIn(str(root / '.veera-artifacts' / 'contract.json'), reason)
        draft = {**payload, 'tool_name': 'Write', 'tool_input': {'file_path': str(root / '.veera-artifacts' / 'contract.json'), 'content': '{}'}}
        self.assertIsNone(safety.evaluate(draft))

    def test_host_saved_tool_output_of_this_session_is_readable(self):
        config = self.base / 'claude-config'
        own = config / 'projects' / 'C--repo' / self.session_id / 'tool-results' / 'b1.txt'
        other = config / 'projects' / 'C--repo' / 'another-session' / 'tool-results' / 'b1.txt'
        with patch.dict('os.environ', {'CLAUDE_CONFIG_DIR': str(config)}):
            self.assertIsNone(self.hook('Read', {'file_path': str(own)}))
            self.assertIn('outside this task', self.hook('Read', {'file_path': str(other)}))
            self.assertIn('outside this task', self.hook('Read', {'file_path': str(config / 'projects' / 'C--repo' / 'notes.md')}))

    def test_redirect_spells_out_the_controller_form(self):
        with patch.dict('os.environ', {'CLAUDE_PLUGIN_DATA': str(self.base / 'plugin-data')}):
            reason = self.hook('Bash', {'command': 'printenv CLAUDE_PLUGIN_DATA'})
        for part in ('CLAUDE_PLUGIN_DATA="' + str(self.base / 'plugin-data') + '"', str(Path(d.__file__).resolve()),
                     self.session_id, str(self.capability), 'docker exec'):
            self.assertIn(part, reason)

    def test_anchored_chains_and_container_tests(self):
        allowed = [self.anchored('git status --short && python -m pytest -q 2>/dev/null | tail -5'),
                   self.anchored('cd tests && python -m unittest -q || git diff'),
                   self.anchored('PYTHONPATH=src python -m pytest testing/test_capture.py -q'),
                   self.anchored('bash run_tests.sh auth_tests'),
                   self.anchored('docker exec ctr bash -lc "source /opt/conda/bin/activate testbed && cd /work/repo && PYTHONPATH=/work/repo python -m pytest -q"'),
                   self.anchored('docker exec -w /work/repo ctr bash /work/repo/run_tests.sh auth_tests 2>&1 | tail -30')]
        for command in allowed:
            with self.subTest(command=command):
                self.assertIsNone(self.hook('Bash', {'command': command}))
                self.assertIsNone(self.hook('PowerShell', {'command': command.replace(' && ', '; ', 1)}))

    def test_read_only_inspection_runs_from_original_checkout(self):
        # The shell starts in the original checkout; reading it or the worktree
        # needs no anchor, so plain pwd, ls and git status never dead-end.
        allowed = [('Bash', 'pwd'), ('Bash', 'ls'), ('Bash', 'git status --short'), ('Bash', 'git log --oneline -2'),
                   ('Bash', 'git worktree list'), ('Bash', 'sed -n 55,110p app.py'), ('Bash', 'cat app.py | head -5'),
                   ('Bash', 'grep -n value app.py; git diff --stat'), ('Bash', 'grep -rn value "' + str(self.root) + '" 2>/dev/null | head'),
                   ('Bash', 'find . -name "*.py"'), ('Bash', 'cd "' + str(self.root) + '" && git log -1 && ls'),
                   ('PowerShell', 'Get-ChildItem'), ('PowerShell', 'Get-Content "' + str(self.root / 'app.py') + '" | Select-Object -First 5')]
        for tool, command in allowed:
            with self.subTest(command=command):
                self.assertIsNone(self.hook(tool, {'command': command}))
        nested = self.original / 'vendor'
        nested.mkdir()
        (nested / '.git').mkdir()
        refused = ['sed -i s/1/2/ app.py', 'sed -n 1p app.py > out.txt', 'sed -n 1w out.txt app.py', 'find . -delete',
                   'find . -exec cat {} +', 'git -c core.pager=less log', 'git diff --output=out.txt', 'git checkout main',
                   'git grep -Oless value', 'sort -o out.txt app.py', 'rg --pre ./x value', 'cat ../foreign/secret.txt',
                   'cat "' + str(self.base / 'foreign' / 'secret.txt') + '"', 'grep -r x "' + str(nested) + '"', 'ls && python -m pytest',
                   'cat app.py | tee out.txt', 'cd .. && ls', 'printenv', 'docker run -v /:/host image', 'echo $(whoami)',
                   'ls "' + str(self.root) + '" && rm -rf "' + str(self.root) + '"']
        for command in refused:
            with self.subTest(command=command):
                reason = self.hook('Bash', {'command': command})
                self.assertIsNotNone(reason)
                self.assertFalse(reason.startswith('ASK:'))

    def test_container_tests_run_from_original_checkout(self):
        # Container-side paths are the container's; the host folder plays no part.
        for command in ('docker exec ctr bash -lc "source /opt/conda/bin/activate testbed && cd /work/repo-bound && python -m pytest -q"',
                        'docker exec -w /testbed ctr python -m pytest tests/test_app.py 2>&1 | tail -30'):
            with self.subTest(command=command):
                self.assertIsNone(self.hook('Bash', {'command': command}))
                self.assertIsNone(self.hook('PowerShell', {'command': command}))
        d.stop(self.root, 'stop')
        self.assertIn('no further', self.hook('Bash', {'command': 'docker exec ctr python -m pytest'}))

    def test_controller_output_may_be_trimmed(self):
        data = str(self.base / 'plugin-data')
        verify = self.controller('verify-local')
        with patch.dict('os.environ', {'CLAUDE_PLUGIN_DATA': data}):
            for command in (f'CLAUDE_PLUGIN_DATA="{data}" VEERA_HOST=claude {verify} 2>&1 | tail -20',
                            f'{verify} | grep -v "^ok" | head -40', f'{verify} 2>&1'):
                with self.subTest(command=command):
                    self.assertIsNone(self.hook('Bash', {'command': command}))
            for command in (f'{verify} | tee out.txt', f'{verify} | tail /etc/passwd', f'{verify} 2>&1 | tail -5 && ls'):
                with self.subTest(command=command):
                    self.assertIn('shell starts in the original checkout', self.hook('Bash', {'command': command}))
            resume = self.controller('resume', f' --file "{self.root / "approval.json"}"')
            self.assertTrue(self.hook('Bash', {'command': f'{resume} 2>&1 | tail -5'}).startswith('ASK:'))

    def test_controller_forms_from_measured_runs(self):
        # Git Bash spells the host interpreter /c/...; scripts name the worktree once
        # in a shell variable; a read or diff may come before the call.
        data = str(self.base / 'plugin-data')
        exe = str(Path(sys.executable).resolve())
        bash = lambda path: '/' + path[0].lower() + path[2:].replace('\\', '/') if path[1:2] == ':' else path
        bash_exe = bash(exe)
        script = str(Path(d.__file__).resolve())
        owner = f'--session-id {self.session_id} --capability-file "{self.capability}"'
        init = f'"{bash_exe}" "{script}" init --root "$T" {owner} --mode fix --request fix --contract "$T/.veera-artifacts/contract.json" --minutes 30 --hard-minutes 60'
        verify = f'VEERA_HOST=claude "{bash_exe}" "{script}" verify-local --root "{self.root}" {owner}'
        allowed = [f'export CLAUDE_PLUGIN_DATA="{data}" VEERA_HOST=claude; T="{self.root}"; {init}',
                   f'T="{self.root}"; cd "$T" && CLAUDE_PLUGIN_DATA="{data}" {init} 2>&1 | tail -20',
                   f'export CLAUDE_PLUGIN_DATA="{data}" VEERA_HOST=claude; {verify}',
                   self.anchored(f'CLAUDE_PLUGIN_DATA="{data}" {verify}'),
                   self.anchored(f'git diff --stat && CLAUDE_PLUGIN_DATA="{data}" {verify}'),
                   self.anchored(f'cd tests 2>/dev/null; git status --short && {verify} | tail -5'),
                   f'"{bash_exe}" "{script}" verify-local --root "{bash(str(self.root))}" --session-id {self.session_id} --capability-file "{bash(str(self.capability))}"']
        with patch.dict('os.environ', {'CLAUDE_PLUGIN_DATA': data}):
            for command in allowed:
                with self.subTest(command=command):
                    self.assertIsNone(self.hook('Bash', {'command': command}))
            refused = [f'T="{self.root}"; PATH=/tmp; {init}', f'PYTHONPATH=/tmp; T="{self.root}"; {init}',
                       f'export T="{self.root}"; {init}', f"T='{self.root}'; echo '$T' && {init}",
                       f'git diff --stat && {verify}', self.anchored(f'rm -rf build && {verify}'),
                       self.anchored(f'ls | sh && {verify}'), self.anchored(f'cat "{self.base / "foreign" / "secret.txt"}" && {verify}'),
                       self.anchored(f'{verify} && ls'), self.anchored(f'git diff || {verify}'), f'T=$(pwd); {init}',
                       f'"{bash_exe}x" "{script}" status --root "{self.root}" {owner}']
            for command in refused:
                with self.subTest(command=command):
                    reason = self.hook('Bash', {'command': command})
                    self.assertIsNotNone(reason)
                    self.assertFalse(reason.startswith('ASK:'))
            # The call itself is still judged bare: authority still asks.
            resume = f'"{bash_exe}" "{script}" resume --root "{self.root}" {owner} --file "{self.root / "approval.json"}"'
            self.assertTrue(self.hook('Bash', {'command': self.anchored(f'git diff --stat && {resume}')}).startswith('ASK:'))
            self.assertTrue(self.hook('Bash', {'command': f'T=x; {resume}'}).startswith('ASK:'))
            # A finished run reads its status bare, but runs nothing before it.
            d.stop(self.root, 'stop')
            status = f'"{bash_exe}" "{script}" status --root "{self.root}"'
            self.assertIsNone(self.hook('Bash', {'command': status}))
            self.assertIn('no further', self.hook('Bash', {'command': self.anchored('git diff --stat && ' + status)}))

    def test_commit_in_worktree_with_inline_author_and_message_body(self):
        commit = 'git -c user.name=Fixture -c user.email=fixture@example.invalid commit -q -m "Fix mode\n\nBody line."'
        self.assertIsNone(self.hook('Bash', {'command': self.anchored('git add app.py && ' + commit)}))
        for command in (self.anchored('git -c core.pager=less log'), self.anchored('git -c core.hooksPath=x commit -m y'),
                        self.anchored('ls\npython -m pytest'), self.anchored('git commit -m "a" \n rm x')):
            with self.subTest(command=command):
                reason = self.hook('Bash', {'command': command})
                self.assertIsNotNone(reason)
                self.assertFalse(reason.startswith('ASK:'))

    def test_plugin_package_is_readable(self):
        plugin = Path(safety.__file__).resolve().parents[1]
        self.assertIsNone(self.hook('Grep', {'pattern': 'anchored', 'path': str(plugin / 'scripts' / 'safety.py')}))
        self.assertIsNone(self.hook('Read', {'file_path': str(plugin / 'hooks' / 'hooks.json')}))

    def test_handle_denies_rather_than_prompts(self):
        result = safety.handle({'session_id': self.session_id, 'cwd': str(self.original), 'tool_name': 'Bash', 'tool_input': {'command': 'python -m pytest'}})
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')
        self.assertEqual(safety.handle({'session_id': self.session_id, 'cwd': str(self.original), 'tool_name': 'Read', 'tool_input': {'file_path': str(self.root / 'app.py')}}), {})


if __name__ == '__main__':
    unittest.main()
