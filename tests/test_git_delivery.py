import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d
import git_delivery as g


class GitDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.original = self.base / 'app'
        self.remote = self.base / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(self.remote)], check=True)
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.original)], check=True)
        g.git(self.original, 'config', 'user.email', 'fixture@example.invalid')
        g.git(self.original, 'config', 'user.name', 'Fixture')
        (self.original / 'app.py').write_text('value = 1\n')
        (self.original / 'VERSION').write_text('1.2.3\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-m', 'Fixture baseline')
        g.git(self.original, 'remote', 'add', 'origin', str(self.remote))
        g.git(self.original, 'push', '-u', 'origin', 'main')
        self.initial = g.git(self.original, 'rev-parse', 'HEAD')
        self.root = Path(g.workspace(self.original, 'fix')['root'])
        self.contract = {'scope': ['app.py', 'VERSION'], 'criteria': [{'id': 'C1', 'text': 'Correct value', 'checks': ['unit']}], 'checks': [{'id': 'unit', 'kind': 'test', 'argv': [sys.executable, '-B', '-c', "from app import value; assert value == 2; print('Ran 1 test')"], 'count_pattern': r'Ran (\d+) test'}], 'release': {'remote': 'origin', 'branch': 'main', 'version_file': 'VERSION', 'push_authorized': True}}

    def start(self, minutes=1, hard_minutes=2):
        return d.init(self.root, 'fix', 'Correct value', self.contract, minutes, hard_minutes)

    def implement(self):
        d.phase(self.root, 'plan')
        d.phase(self.root, 'implement')
        (self.root / 'app.py').write_text('value = 2\n')

    def ready(self):
        g.prepare(self.root)
        d.phase(self.root, 'verify')
        self.assertEqual(d.check(self.root, 'unit')['status'], 'passed')
        d.phase(self.root, 'review')
        d.review(self.root, {'reviewer': 'fixture-independent', 'fingerprint': d.digest(d.snapshot(self.root)), 'approved': True, 'criteria': ['C1'], 'notes': 'Fixture attestation, not a real agent'})
        self.assertEqual(d.finish(self.root)['status'], 'ready')

    def test_complete_release_once(self):
        self.start()
        self.implement()
        self.ready()
        self.assertEqual((self.original / 'app.py').read_text(), 'value = 1\n')
        # Fixture user explicitly frees main; Veera must never do this itself.
        g.git(self.original, 'switch', '--detach')
        result = g.publish(self.root)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual((self.original / 'app.py').read_text(), 'value = 1\n')
        self.assertEqual((self.original / 'VERSION').read_text(), '1.2.3\n')
        self.assertEqual(g.git(self.original, 'rev-parse', 'main'), self.initial)
        self.assertEqual(g.git(self.root, 'rev-parse', 'HEAD'), g.git(self.remote, 'rev-parse', 'main'))
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)

    def test_topic_branch_commits_not_silently_included(self):
        g.git(self.original, 'switch', '-c', 'unrelated-topic')
        (self.original / 'unrelated.txt').write_text('not this task')
        g.git(self.original, 'add', 'unrelated.txt')
        g.git(self.original, 'commit', '-m', 'Unrelated topic')
        with self.assertRaises(d.DeliveryError):
            g.workspace(self.original, 'unsafe')

    def test_open_blocker_blocks_final_push(self):
        import task_context as c
        import hashlib
        self.start()
        self.implement()
        self.ready()
        evidence = self.root / '.veera-artifacts/blocker.txt'
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text('New regression found before publication')
        state = d.status(self.root)
        c.blocker(self.root, {'run_id': state['run_id'], 'op': 'open', 'family': 'test', 'target': 'unit', 'criteria': ['C1'], 'evidence': [{'path': '.veera-artifacts/blocker.txt', 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}]})
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)
        self.assertFalse(d.status(self.root).get('push_attempted'))
        self.assertEqual(g.git(self.remote, 'rev-parse', 'main'), self.initial)

    def test_preinit_worktree_commit_cannot_become_baseline(self):
        (self.root / 'unrelated.txt').write_text('unapproved commit')
        g.git(self.root, 'add', 'unrelated.txt')
        g.git(self.root, 'commit', '-m', 'Unexpected before-init commit')
        with self.assertRaises(d.DeliveryError):
            self.start()
        self.assertEqual(g.git(self.remote, 'rev-parse', 'main'), self.initial)

    def test_preinit_uncommitted_source_refused(self):
        (self.root / 'app.py').write_text('changed before contract')
        with self.assertRaises(d.DeliveryError):
            self.start()

    def test_ignored_application_input_refused_upfront(self):
        with (g.common(self.root) / 'info/exclude').open('a') as stream:
            stream.write('\nprivate-input.txt\n')
        (self.root / 'private-input.txt').write_text('runtime input')
        self.contract['scope'].append('private-input.txt')
        with self.assertRaises(d.DeliveryError):
            self.start()

    def test_ignored_peer_collision_blocks_before_push(self):
        self.contract['scope'].append('peer.txt')
        self.start()
        self.implement()
        (self.root / 'peer.txt').write_text('task content')
        g.git(self.root, 'add', 'peer.txt')
        with (g.common(self.root) / 'info/exclude').open('a') as stream:
            stream.write('\npeer.txt\n')
        (self.original / 'peer.txt').write_text('precious ignored peer work')
        self.ready()
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)
        self.assertEqual((self.original / 'peer.txt').read_text(), 'precious ignored peer work')
        self.assertFalse(d.status(self.root).get('push_attempted'))
        self.assertEqual(g.git(self.remote, 'rev-parse', 'main'), self.initial)

    def test_major_version_edit_refused(self):
        self.start()
        self.implement()
        (self.root / 'VERSION').write_text('9.0.0\n')
        with self.assertRaises(d.DeliveryError):
            g.prepare(self.root)
        self.assertEqual(g.git(self.remote, 'rev-parse', 'main'), self.initial)

    def test_visual_artifact_change_blocks_publication(self):
        self.contract['checks'].append({'id': 'visual', 'kind': 'visual', 'argv': [sys.executable, '-c', "from pathlib import Path; Path('.veera-artifacts').mkdir(exist_ok=True); Path('.veera-artifacts/view.png').write_bytes(b'fixture-image')"], 'artifacts': ['.veera-artifacts/view.png']})
        self.start()
        self.implement()
        g.prepare(self.root)
        d.phase(self.root, 'verify')
        d.check(self.root, 'unit')
        d.check(self.root, 'visual')
        d.phase(self.root, 'review')
        d.review(self.root, {'reviewer': 'fixture-independent', 'fingerprint': d.digest(d.snapshot(self.root)), 'approved': True, 'criteria': ['C1'], 'notes': 'Fixture'})
        d.finish(self.root)
        (self.root / '.veera-artifacts/view.png').write_bytes(b'changed')
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)
        self.assertFalse(d.status(self.root).get('push_attempted'))

    def test_reject_init_outside_worktree(self):
        with self.assertRaises((d.DeliveryError, FileNotFoundError)):
            d.init(self.original, 'fix', 'Fix', self.contract, 1, 2)

    def test_soft_target_does_not_abandon_work(self):
        self.start(minutes=.0001)
        time.sleep(.02)
        state = d.status(self.root)
        self.assertEqual(state['status'], 'active')
        self.assertTrue(state['replan_required'])
        deadline = state['deadline']
        state = d.decision(self.root, {'owner': 'pm', 'consulted': ['architect', 'advisor'], 'decision': 'Reuse existing tests and continue full acceptance', 'reason': 'Soft target reached; time remains'})
        self.assertFalse(state['replan_required'])
        self.assertEqual(state['deadline'], deadline)

    def test_hard_stop_preserves_main(self):
        self.start(minutes=.0001, hard_minutes=.0002)
        time.sleep(.03)
        self.assertEqual(d.status(self.root)['status'], 'budget-exhausted')
        self.assertEqual(g.git(self.original, 'rev-parse', 'HEAD'), self.initial)
        self.assertEqual(g.git(self.remote, 'rev-parse', 'main'), self.initial)

    def test_resume_preserves_counters_and_requires_fresh_checkpoint(self):
        self.start()
        self.implement()
        d.stop(self.root, 'explicit user interruption')
        saved = d.checkpoint(self.root, 'Preserve exact work')
        report = {'checkpoint_id': saved['checkpoint']['id'], 'authorization': 'User explicitly resumes this task', 'reason': 'Interruption cleared', 'additional_minutes': 0}
        original_started = saved['started_at']
        resumed = d.resume(self.root, report)
        self.assertEqual(resumed['started_at'], original_started)
        self.assertEqual(resumed['repairs'], saved['repairs'])
        self.assertEqual(resumed['status'], 'active')
        d.stop(self.root, 'interrupt again')
        d.checkpoint(self.root, 'new checkpoint')
        with self.assertRaises(d.DeliveryError):
            d.resume(self.root, report)

    def test_dirty_original_refuses_workspace(self):
        (self.original / 'peer.txt').write_text('peer work')
        with self.assertRaises(d.DeliveryError):
            g.workspace(self.original, 'another')
        self.assertEqual((self.original / 'peer.txt').read_text(), 'peer work')

    def test_dirty_main_blocks_publish_preserves_peer(self):
        self.start()
        self.implement()
        self.ready()
        (self.original / 'peer.txt').write_text('peer work')
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)
        self.assertFalse(d.status(self.root).get('push_attempted'))
        self.assertEqual((self.original / 'peer.txt').read_text(), 'peer work')
        self.assertEqual(g.git(self.remote, 'rev-parse', 'main'), self.initial)

    def test_concurrent_main_integrated_before_final_tests(self):
        self.start()
        self.implement()
        (self.original / 'parallel.py').write_text('parallel = True\n')
        g.git(self.original, 'add', 'parallel.py')
        g.git(self.original, 'commit', '-m', 'Parallel completed change')
        g.git(self.original, 'push', 'origin', 'main')
        self.ready()
        self.assertTrue((self.root / 'parallel.py').exists())
        g.git(self.original, 'switch', '--detach')
        g.publish(self.root)
        self.assertTrue((self.original / 'parallel.py').exists())

    def test_remote_change_after_review_blocks_before_push(self):
        self.start()
        self.implement()
        self.ready()
        (self.original / 'parallel.py').write_text('parallel = True\n')
        g.git(self.original, 'add', 'parallel.py')
        g.git(self.original, 'commit', '-m', 'Parallel change')
        g.git(self.original, 'push', 'origin', 'main')
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)
        self.assertFalse(d.status(self.root).get('push_attempted'))

    def test_reconcile_latest_main_then_reverify_and_push_once(self):
        self.start()
        self.implement()
        self.ready()
        (self.original / 'parallel.py').write_text('parallel = True\n')
        g.git(self.original, 'add', 'parallel.py')
        g.git(self.original, 'commit', '-m', 'Parallel change')
        g.git(self.original, 'push', 'origin', 'main')
        g.reconcile(self.root, 'Main advanced; retain scope and revalidate integrated tree')
        self.assertEqual((self.root / 'VERSION').read_text(), '1.2.4\n')
        self.ready()
        g.git(self.original, 'switch', '--detach')
        self.assertEqual(g.publish(self.root)['status'], 'complete')
        self.assertTrue((self.original / 'parallel.py').exists())

    def test_version_bump_idempotent(self):
        self.start()
        self.implement()
        first = g.prepare(self.root)
        second = g.prepare(self.root)
        self.assertEqual(first['release_prepared'], second['release_prepared'])
        self.assertEqual((self.root / 'VERSION').read_text(), '1.2.4\n')

    def test_stale_code_cannot_publish(self):
        self.start()
        self.implement()
        self.ready()
        (self.root / 'app.py').write_text('value = 3\n')
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)
        self.assertEqual(g.git(self.remote, 'rev-parse', 'main'), self.initial)

    def test_rejected_push_not_retried(self):
        self.start()
        self.implement()
        self.ready()
        g.git(self.original, 'switch', '--detach')
        # A checked-out receive branch with denyCurrentBranch=refuse gives an
        # actual Git rejection without relying on executable /tmp hooks.
        g.git(self.remote, 'config', 'core.bare', 'false')
        g.git(self.remote, 'symbolic-ref', 'HEAD', 'refs/heads/main')
        g.git(self.remote, 'config', 'receive.denyCurrentBranch', 'refuse')
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)
        state = d.status(self.root)
        self.assertEqual(state['status'], 'blocked')
        self.assertIsNotNone(state['push_attempted'])
        self.assertEqual(g.git(self.original, 'rev-parse', 'HEAD'), self.initial)
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)

    def test_failed_test_never_publishes(self):
        self.start()
        d.phase(self.root, 'plan')
        d.phase(self.root, 'implement')
        g.prepare(self.root)
        d.phase(self.root, 'verify')
        self.assertEqual(d.check(self.root, 'unit')['status'], 'failed')
        with self.assertRaises(d.DeliveryError):
            g.publish(self.root)
        self.assertEqual(g.git(self.remote, 'rev-parse', 'main'), self.initial)

    def local_contract(self):
        self.contract['delivery_mode'] = 'local-verify'
        self.contract.pop('release')
        self.contract['scope'] = ['app.py']

    def local_review(self):
        d.phase(self.root, 'verify')
        result = d.check(self.root, 'unit')
        d.phase(self.root, 'review')
        d.review(self.root, {'reviewer': 'fixture-independent', 'fingerprint': d.digest(d.snapshot(self.root)), 'approved': True, 'criteria': ['C1'], 'notes': 'Fixture attestation'})
        return result

    def test_local_verification_without_remote_or_version_authority(self):
        self.local_contract()
        g.git(self.root, 'remote', 'remove', 'origin')
        self.start()
        self.implement()
        self.assertEqual(self.local_review()['test_count'], 1)
        result = d.finish(self.root)
        self.assertEqual(result['status'], 'verified-local')
        self.assertIn(result['status'], d.TERMINAL)
        self.assertNotIn('release_prepared', result)
        self.assertNotIn('push_attempted', result)
        self.assertEqual(g.git(self.root, 'rev-parse', 'HEAD'), self.initial)
        self.assertEqual(g.git(self.remote, 'rev-parse', 'main'), self.initial)
        self.assertEqual((self.root / 'VERSION').read_text(), '1.2.3\n')
        self.assertEqual((self.original / 'app.py').read_text(), 'value = 1\n')
        with self.assertRaises(d.DeliveryError):
            d.phase(self.root, 'review')
        self.assertEqual(d.stop(self.root, 'stop')['status'], 'verified-local')

    def test_local_mode_rejects_every_release_operation_before_side_effects(self):
        self.local_contract()
        self.start()
        self.implement()
        original_git = g.git
        def read_only_git(root, *args, **kwargs):
            self.assertIn(args[0], ('rev-parse', 'branch'))
            return original_git(root, *args, **kwargs)
        with patch.object(g, 'git', side_effect=read_only_git):
            for operation in (g.prepare, g.publish, lambda root: g.reconcile(root, 'new main')):
                with self.subTest(operation=operation), self.assertRaisesRegex(d.DeliveryError, 'Local verification prohibits'):
                    operation(self.root)
        self.assertEqual(g.git(self.root, 'rev-parse', 'HEAD'), self.initial)

    def test_local_mode_rejects_release_configuration(self):
        self.contract['delivery_mode'] = 'local-verify'
        with self.assertRaisesRegex(d.DeliveryError, 'must omit release'):
            self.start()

    def assert_local_terminal_hook(self, handler, edit_tool, edit_input, execute_tool, execute_input):
        import ownership
        self.enterContext(patch.object(ownership, 'REGISTRY', self.base / 'sessions'))
        session = 'fixture-terminal-owner'
        self.root = Path(g.workspace(self.original, 'terminal', session)['root'])
        self.local_contract()
        self.start()
        self.implement()
        payload = {'session_id': session, 'cwd': str(self.root), 'hook_event_name': 'PreToolUse'}
        edit = {**payload, 'tool_name': edit_tool, 'tool_input': edit_input(self.root)}
        self.assertEqual(handler(edit), {}, 'Owned in-scope edit must be allowed during implementation')
        self.local_review()
        self.assertEqual(d.finish(self.root)['status'], 'verified-local')
        for request in (edit, {**payload, 'tool_name': execute_tool, 'tool_input': execute_input}):
            with self.subTest(tool=request['tool_name']):
                result = handler(request)['hookSpecificOutput']
                self.assertEqual(result['permissionDecision'], 'deny')
                self.assertIn('verified-local', result['permissionDecisionReason'])
        self.assertEqual(handler({**payload, 'tool_name': 'Read', 'tool_input': {'file_path': str(self.root / 'app.py')}}), {})
        self.assertEqual(d.status(self.root)['status'], 'verified-local')
        self.assertEqual((self.root / 'app.py').read_text(), 'value = 2\n')

    def test_claude_hook_denies_source_edits_after_local_verification(self):
        import safety
        self.assert_local_terminal_hook(safety.handle, 'Edit', lambda root: {'file_path': str(root / 'app.py'), 'old_string': 'value = 2', 'new_string': 'value = 3'}, 'Bash', {'command': 'python3 app.py'})

    def test_codex_hook_denies_source_patches_after_local_verification(self):
        self.enterContext(patch.dict(os.environ, {'VEERA_HOST': 'codex'}))
        import codex_hook
        self.assert_local_terminal_hook(codex_hook.handle, 'apply_patch', lambda root: {'command': '*** Begin Patch\n*** Update File: ' + str(root / 'app.py') + '\n@@\n-value = 2\n+value = 3\n*** End Patch\n'}, 'exec_command', {'cmd': 'python3 app.py'})

    def test_public_cli_local_init_retains_session_ownership(self):
        import ownership
        from session_fixture import cli
        self.local_contract()
        self.enterContext(patch.object(ownership, 'REGISTRY', self.base / 'sessions'))
        self.session_id = 'fixture-local-owner'
        metadata = d.read_json(self.root / '.veera/workspace.json')
        metadata['session_id'] = self.session_id
        d.atomic(self.root / '.veera/workspace.json', metadata)
        self.capability = ownership.enroll(self.session_id, self.root, metadata['id'])
        contract_path = self.root / '.veera-artifacts/contract.json'
        contract_path.parent.mkdir()
        contract_path.write_text(json.dumps(self.contract))
        arguments = ('init', '--root', str(self.root), '--mode', 'fix', '--request', 'Correct value locally', '--contract', str(contract_path))
        owner = self.session_id
        self.session_id = 'foreign-session'
        self.assertEqual(cli(self, *arguments).returncode, 2)
        self.assertFalse((self.root / '.veera/state.json').exists())
        self.session_id = owner
        result = cli(self, *arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.implement()
        self.local_review()
        result = cli(self, 'finish', '--root', str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'verified-local')
        self.assertEqual(cli(self, 'publish', '--root', str(self.root)).returncode, 2)
        self.assertEqual(cli(self, 'unbind', '--root', str(self.root)).returncode, 2)
        self.assertTrue(Path(self.capability).is_file())

    def test_delivery_mode_typo_fails_closed(self):
        self.contract['delivery_mode'] = 'local'
        with self.assertRaisesRegex(d.DeliveryError, 'Unknown delivery_mode'):
            self.start()

    def test_publish_default_still_requires_authority(self):
        self.contract['release']['push_authorized'] = False
        with self.assertRaisesRegex(d.DeliveryError, 'authorization'):
            self.start()

    def test_local_mode_cannot_use_legacy_unowned_lifecycle(self):
        self.local_contract()
        with self.assertRaisesRegex(d.DeliveryError, 'owned-worktree'):
            d.init(self.original, 'fix', 'Fix', self.contract, 1)
        with self.assertRaises((d.DeliveryError, FileNotFoundError)):
            d.init(self.original, 'fix', 'Fix', self.contract, 1, 2)

    def test_local_mode_is_frozen_by_contract_checksum(self):
        self.local_contract()
        self.start()
        path = self.root / '.veera/state.json'
        state = d.read_json(path)
        state['contract']['delivery_mode'] = 'publish'
        d.atomic(path, state)
        with self.assertRaisesRegex(d.DeliveryError, 'integrity'):
            d.status(self.root)

    def test_local_finish_rejects_zero_count(self):
        self.local_contract()
        self.contract['checks'][0]['argv'][-1] = "print('Ran 0 tests')"
        self.start()
        self.implement()
        self.assertEqual(self.local_review()['status'], 'failed')
        with self.assertRaisesRegex(d.DeliveryError, 'failed or stale'):
            d.finish(self.root)

    def test_local_finish_rejects_changed_source(self):
        self.local_contract()
        self.start()
        self.implement()
        self.local_review()
        (self.root / 'app.py').write_text('value = 3\n')
        with self.assertRaisesRegex(d.DeliveryError, 'stale'):
            d.finish(self.root)

    def test_local_finish_rejects_missing_independent_review(self):
        self.local_contract()
        self.start()
        self.implement()
        d.phase(self.root, 'verify')
        d.check(self.root, 'unit')
        d.phase(self.root, 'review')
        with self.assertRaisesRegex(d.DeliveryError, 'independent review'):
            d.finish(self.root)

    def test_local_finish_rejects_open_blocker(self):
        import task_context as c
        self.local_contract()
        state = self.start()
        self.implement()
        self.local_review()
        evidence = self.root / '.veera-artifacts/blocker.txt'
        evidence.parent.mkdir(exist_ok=True)
        evidence.write_text('Unresolved acceptance issue')
        c.blocker(self.root, {'run_id': state['run_id'], 'op': 'open', 'family': 'test', 'target': 'unit', 'criteria': ['C1'], 'evidence': [{'path': '.veera-artifacts/blocker.txt', 'sha256': d.hashlib.sha256(evidence.read_bytes()).hexdigest()}]})
        with self.assertRaises(d.DeliveryError):
            d.finish(self.root)

    @unittest.skipIf(sys.version_info < (3, 11), 'Cargo TOML parsing requires Python 3.11+')
    def test_cargo_workspace_prepare_reconcile_preserves_other_text(self):
        original = '# shared release\n[workspace]\nmembers = []\n[workspace.package] # metadata\nversion = "1.2.3" # keep\nedition = "2021"\n\n[profile.release]\nlto = true\n'
        # Fixture setup occurs before the task lifecycle; no real repository config.
        (self.root / 'Cargo.toml').write_text(original)
        g.git(self.root, 'add', 'Cargo.toml')
        g.git(self.root, 'commit', '-m', 'Fixture Cargo manifest')
        tip = g.git(self.root, 'rev-parse', 'HEAD')
        g.git(self.root, 'push', 'origin', 'HEAD:main')
        metadata = d.read_json(self.root / '.veera/workspace.json')
        metadata['base'] = tip
        d.atomic(self.root / '.veera/workspace.json', metadata)
        self.contract['scope'] = ['app.py', 'Cargo.toml']
        self.contract['release']['version_file'] = 'Cargo.toml'
        self.start()
        self.implement()
        g.prepare(self.root)
        expected = original.replace('"1.2.3"', '"1.2.4"')
        self.assertEqual((self.root / 'Cargo.toml').read_text(), expected)
        g.reconcile(self.root, 'Reconfirm latest main')
        self.assertEqual((self.root / 'Cargo.toml').read_text(), expected)


class VersionTests(unittest.TestCase):
    @unittest.skipIf(sys.version_info < (3, 11), 'Cargo TOML parsing requires Python 3.11+')
    def test_cargo_changes_only_exact_version_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Cargo.toml'
            original = b"# version 1.2.3\r\n[workspace.package]\r\nversion\t= '1.2.3' # release\r\nedition = '2021'\r\n[dependencies]\r\nexample = '1.2.3'\r\n"
            path.write_bytes(original)
            self.assertEqual(g.version_value(path), ('1.2.3', '1.2.4'))
            g.write_version(path, '1.2.4')
            self.assertEqual(path.read_bytes(), original.replace(b"version\t= '1.2.3'", b"version\t= '1.2.4'"))

    def test_cargo_refuses_ambiguous_and_complex_forms(self):
        texts = [
            '[package]\nversion = "1.2.3"\n',
            '[workspace.package]\nversion = "1.2.3-alpha"\n',
            '[workspace.package]\nversion = "01.2.3"\n',
            '[workspace.package]\nversion = { workspace = true }\n',
            '[workspace.package]\nversion = "1.2.3"\nversion = "1.2.4"\n',
            'workspace.package.version = "1.2.3"\n',
            '[workspace.package]\nversion = """1.2.3"""\n',
            '[workspace.package]\nversion = "1.2.3"\n[workspace.package]\n',
            'workspace = "unexpected"\n',
            'description = """\n[workspace.package]\nversion = "1.2.3"\n"""\n[workspace.package]\nversion = "1.2.3"\n',
        ]
        for text in texts:
            with self.subTest(text=text), self.assertRaises(d.DeliveryError):
                g.version_text(Path('Cargo.toml'), text)

    def test_existing_version_formats_unchanged(self):
        self.assertEqual(g.version_text(Path('package.json'), '{"version":"1.2.3"}'), ('1.2.3', '1.2.4'))
        self.assertEqual(g.version_text(Path('VERSION'), '1.2.3\n'), ('1.2.3', '1.2.4'))


if __name__ == '__main__':
    unittest.main()
