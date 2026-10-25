"""Partial enrollment recovery uses disposable repositories and owner records."""
import contextlib
import io
import json
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


class WorkspaceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.original = self.base / 'original'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.original)], check=True)
        g.git(self.original, 'config', 'user.name', 'Fixture')
        g.git(self.original, 'config', 'user.email', 'fixture@example.invalid')
        (self.original / 'app.py').write_text('value = 1\n')
        g.git(self.original, 'add', 'app.py')
        g.git(self.original, 'commit', '-m', 'Fixture baseline')
        self.tip = g.git(self.original, 'rev-parse', 'HEAD')
        g.git(self.original, 'switch', '--detach')
        self.registry = self.base / 'host-data' / 'sessions'
        self.enterContext(patch.object(ownership, 'REGISTRY', self.registry))
        self.session = 'fixture-owner'
        self.target = self.base / 'original-veera-fix'
        self.metadata_path = self.target / '.veera/workspace.json'
        mkdir = Path.mkdir

        def fail_enrollment(path, *args, **kwargs):
            if path == self.registry:
                raise PermissionError('Fixture host directory permission denied')
            return mkdir(path, *args, **kwargs)

        # Actual enrollment reaches its directory creation and fails after Git and
        # workspace metadata have been created, reproducing the observed ordering.
        with patch.object(Path, 'mkdir', fail_enrollment), self.assertRaises(PermissionError):
            g.workspace(self.original, 'fix', self.session)
        self.metadata = self.metadata_path.read_bytes()
        self.assertIsNone(ownership.lookup(self.session))
        self.assertFalse((self.target / '.veera/state.json').exists())

    def recover(self, session=None):
        return g.workspace(self.original, 'fix', session or self.session)

    def test_public_workspace_retry_recovers_after_main_advances(self):
        peer = self.base / 'peer'
        g.git(self.original, 'worktree', 'add', str(peer), 'main')
        (peer / 'peer.txt').write_text('Unrelated authorized peer work\n')
        g.git(peer, 'add', 'peer.txt')
        g.git(peer, 'commit', '-m', 'Peer advance')
        main_tip = g.git(peer, 'rev-parse', 'HEAD')
        config = (g.common(self.original) / 'config').read_bytes()
        output = io.StringIO()
        with patch.object(sys, 'argv', ['delivery', 'workspace', '--root', str(self.original), '--task', 'fix', '--session-id', self.session]), contextlib.redirect_stdout(output):
            d.main()
        result = json.loads(output.getvalue())
        self.assertTrue(result['recovered'])
        self.assertEqual(result['base'], self.tip)
        self.assertEqual(self.metadata_path.read_bytes(), self.metadata)
        self.assertEqual(g.git(self.target, 'rev-parse', 'HEAD'), self.tip)
        self.assertEqual(g.git(self.original, 'rev-parse', 'HEAD'), self.tip)
        self.assertEqual(g.git(self.original, 'rev-parse', 'main'), main_tip)
        self.assertEqual(g.git(peer, 'rev-parse', 'HEAD'), main_tip)
        self.assertEqual((peer / 'peer.txt').read_text(), 'Unrelated authorized peer work\n')
        self.assertEqual((g.common(self.original) / 'config').read_bytes(), config)
        record = ownership.authorize(self.session, self.target, result['capability_file'])
        self.assertEqual(record['workspace_id'], result['id'])
        binding = Path(result['capability_file']).read_bytes()
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertEqual(Path(result['capability_file']).read_bytes(), binding)

    def test_different_or_missing_owner_cannot_recover(self):
        for owner in ('other-owner', None):
            with self.subTest(owner=owner), self.assertRaises(d.DeliveryError):
                g.workspace(self.original, 'fix', owner)
        self.assertEqual(self.metadata_path.read_bytes(), self.metadata)
        self.assertIsNone(ownership.lookup('other-owner'))

    def test_existing_binding_elsewhere_is_preserved(self):
        path = Path(ownership.enroll(self.session, self.original, 'other-workspace'))
        before = path.read_bytes()
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.metadata_path.read_bytes(), self.metadata)

    def test_dirty_task_cannot_recover(self):
        (self.target / 'app.py').write_text('unexpected edit\n')
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertEqual((self.target / 'app.py').read_text(), 'unexpected edit\n')
        self.assertIsNone(ownership.lookup(self.session))

    def test_changed_task_head_cannot_recover(self):
        g.git(self.target, 'commit', '--allow-empty', '-m', 'Unexpected commit')
        tip = g.git(self.target, 'rev-parse', 'HEAD')
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertEqual(g.git(self.target, 'rev-parse', 'HEAD'), tip)
        self.assertIsNone(ownership.lookup(self.session))

    def test_changed_branch_cannot_recover(self):
        g.git(self.target, 'switch', '-c', 'other-branch')
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertEqual(g.git(self.target, 'branch', '--show-current'), 'other-branch')
        self.assertIsNone(ownership.lookup(self.session))

    def test_changed_task_ref_cannot_recover(self):
        # A direct ref movement changes the checked-out task HEAD without creating
        # a task commit through the normal checkout, and must still be refused.
        tree = g.git(self.original, 'rev-parse', 'HEAD^{tree}')
        moved = g.git(self.original, 'commit-tree', tree, '-p', self.tip, '-m', 'Unexpected ref movement')
        g.git(self.original, 'update-ref', 'refs/heads/veera/fix', moved)
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertEqual(g.git(self.original, 'rev-parse', 'refs/heads/veera/fix'), moved)
        self.assertIsNone(ownership.lookup(self.session))

    def test_changed_git_pointer_cannot_adopt_another_repository(self):
        other = self.base / 'other'
        subprocess.run(['git', 'init', '-q', str(other)], check=True)
        pointer = self.target / '.git'
        # Git marks this file hidden on Windows; truncating a hidden file with
        # CREATE_ALWAYS fails. Replace only this disposable fixture pointer.
        self.assertTrue(pointer.resolve().is_relative_to(self.base.resolve()))
        pointer.unlink()
        pointer.write_text('gitdir: ' + (other / '.git').as_posix() + '\n')
        before = pointer.read_bytes()
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertEqual(pointer.read_bytes(), before)
        self.assertIsNone(ownership.lookup(self.session))

    def test_uncommitted_original_work_neither_blocks_nor_enters_recovery(self):
        (self.original / 'app.py').write_text('value = "peer edit after the failure"\n')
        result = self.recover()
        self.assertTrue(result['recovered'])
        self.assertEqual((result['base'], g.git(self.target, 'rev-parse', 'HEAD')), (self.tip, self.tip))
        self.assertEqual((self.target / 'app.py').read_text(), 'value = 1\n')
        self.assertEqual(self.metadata_path.read_bytes(), self.metadata)

    def test_snapshot_based_workspace_recovers_on_its_recorded_start(self):
        (self.original / 'app.py').write_text('value = "uncommitted"\n')
        target = self.base / 'original-veera-snap'
        mkdir = Path.mkdir

        def fail_enrollment(path, *args, **kwargs):
            if path == self.registry:
                raise PermissionError('Fixture host directory permission denied')
            return mkdir(path, *args, **kwargs)

        with patch.object(Path, 'mkdir', fail_enrollment), self.assertRaises(PermissionError):
            g.workspace(self.original, 'snap', 'snap-owner')
        snapshot = g.git(target, 'rev-parse', 'HEAD')
        self.assertEqual(g.git(target, 'rev-parse', 'HEAD^'), self.tip)
        result = g.workspace(self.original, 'snap', 'snap-owner')
        self.assertTrue(result['recovered'])
        self.assertEqual((result['base'], result['head']), (snapshot, self.tip))
        self.assertEqual((target / 'app.py').read_text(), 'value = "uncommitted"\n')

    def test_changed_original_head_cannot_recover(self):
        g.git(self.original, 'commit', '--allow-empty', '-m', 'Original moved')
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertIsNone(ownership.lookup(self.session))

    def test_initialized_task_cannot_recover(self):
        state = self.target / '.veera/state.json'
        state.write_text('{}')
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertEqual(state.read_text(), '{}')
        self.assertIsNone(ownership.lookup(self.session))

    def test_mismatched_metadata_cannot_override_baseline_or_identity(self):
        for field, value in (('root', str(self.original)), ('original', str(self.base)), ('branch', 'veera/other'), ('base', '0' * 40), ('common', str(self.base)), ('session_id', 'different-owner'), ('id', 'invalid')):
            with self.subTest(field=field):
                metadata = json.loads(self.metadata)
                metadata[field] = value
                self.metadata_path.write_text(json.dumps(metadata))
                before = self.metadata_path.read_bytes()
                with self.assertRaises(d.DeliveryError):
                    self.recover()
                self.assertEqual(self.metadata_path.read_bytes(), before)
                self.assertIsNone(ownership.lookup(self.session))
        self.metadata_path.write_bytes(self.metadata)

    def test_metadata_symlink_cannot_recover(self):
        saved = self.base / 'saved-metadata.json'
        saved.write_bytes(self.metadata)
        self.metadata_path.unlink()
        try:
            self.metadata_path.symlink_to(saved)
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows symlink privilege is unavailable')
            raise
        with self.assertRaises(d.DeliveryError):
            self.recover()
        self.assertIsNone(ownership.lookup(self.session))

    def test_repeated_enrollment_failure_keeps_original_metadata(self):
        with patch.object(ownership, 'enroll', side_effect=PermissionError('Still denied')), self.assertRaises(PermissionError):
            self.recover()
        self.assertEqual(self.metadata_path.read_bytes(), self.metadata)
        self.assertIsNone(ownership.lookup(self.session))
        self.assertTrue(self.recover()['recovered'])


if __name__ == '__main__':
    unittest.main()
