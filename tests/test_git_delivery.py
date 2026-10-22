import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

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


if __name__ == '__main__':
    unittest.main()
