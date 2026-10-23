import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d


class SnapshotGitlinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git('init', '-q')
        tree = self.git('mktree', input=b'').strip()
        self.commits = []
        for message in ('first', 'second'):
            commit = (f'tree {tree}\nauthor Fixture <fixture@example.test> 1 +0000\n'
                      f'committer Fixture <fixture@example.test> 1 +0000\n\n{message}\n')
            self.commits.append(self.git('hash-object', '-t', 'commit', '-w', '--stdin', input=commit.encode()).strip())
        self.name = 'reference/gridcraft'
        self.path = self.root / self.name
        self.pin(self.commits[0])

    def git(self, *args, input=None):
        return subprocess.run(['git', '-C', str(self.root), *args], input=input,
                              capture_output=True, check=True).stdout.decode()

    def pin(self, commit):
        self.git('update-index', '--add', '--cacheinfo', f'160000,{commit},{self.name}')

    def test_absent_and_empty_share_exact_pin(self):
        expected = {self.name: d.digest({'gitlink': self.commits[0]})}
        self.assertEqual(d.snapshot(self.root), expected)
        self.path.mkdir(parents=True)
        self.assertEqual(d.snapshot(self.root), expected)

    def test_index_commit_change_changes_fingerprint(self):
        before = d.snapshot(self.root)
        self.pin(self.commits[1])
        self.assertEqual(d.snapshot(self.root)[self.name], d.digest({'gitlink': self.commits[1]}))
        self.assertNotEqual(before, d.snapshot(self.root))

    def test_nonempty_including_ignored_contents_refused(self):
        self.path.mkdir(parents=True)
        (self.root / '.gitignore').write_text('reference/\n')
        (self.path / 'ignored').write_text('content')
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root)

    def test_replacement_file_refused(self):
        self.path.parent.mkdir()
        self.path.write_text('replacement')
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root)

    def test_file_ancestor_refused(self):
        self.path.parent.write_text('replacement ancestor')
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root)

    def test_initialized_submodule_refused(self):
        self.path.mkdir(parents=True)
        (self.path / '.git').write_text('gitdir: ../../.git/modules/gridcraft\n')
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root)

    def test_index_path_with_spaces_preserved(self):
        self.git('update-index', '--force-remove', self.name)
        self.name = 'reference/with spaces'
        self.pin(self.commits[0])
        self.assertEqual(d.snapshot(self.root), {self.name: d.digest({'gitlink': self.commits[0]})})

    def test_scoped_ignored_contents_refused(self):
        self.path.mkdir(parents=True)
        (self.root / '.gitignore').write_text('reference/\n')
        (self.path / 'ignored').write_text('content')
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root, scope=['reference'])

    def test_ordinary_indexed_file_replaced_by_directory_refused(self):
        path = self.root / 'ordinary'
        path.write_text('content')
        self.git('add', 'ordinary')
        path.unlink()
        path.mkdir()
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root)

    def test_unmerged_gitlinks_refused(self):
        self.git('update-index', '--force-remove', self.name)
        records = ''.join(f'160000 {commit} {stage}\t{self.name}\n'
                          for stage, commit in enumerate(self.commits, 1))
        self.git('update-index', '--index-info', input=records.encode())
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root)

    def symlink(self, target, path):
        try:
            path.symlink_to(target, target_is_directory=True)
        except OSError as error:
            self.skipTest(f'Host cannot create fixture symlinks: {error}')

    def test_leaf_symlink_refused(self):
        self.path.parent.mkdir()
        self.symlink(self.root / 'missing', self.path)
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root)

    def test_symlink_ancestor_refused(self):
        target = self.root / 'target'
        target.mkdir()
        self.symlink(target, self.path.parent)
        with self.assertRaises(d.DeliveryError):
            d.snapshot(self.root)

    def test_ordinary_files_and_deletion_unchanged(self):
        for name in ('tracked', 'deleted', 'untracked'):
            (self.root / name).write_bytes(b'content')
        self.git('add', 'tracked', 'deleted')
        (self.root / 'deleted').unlink()
        result = d.snapshot(self.root)
        self.assertEqual(result['deleted'], 'deleted')
        for name in ('tracked', 'untracked'):
            expected = hashlib.sha256(b'content' + str((self.root / name).stat().st_mode & 0o777).encode()).hexdigest()
            self.assertEqual(result[name], expected)

    def test_ordinary_symlink_unchanged(self):
        path = self.root / 'link'
        self.symlink(self.root / 'missing', path)
        self.assertEqual(d.snapshot(self.root)['link'], d.digest({'symlink': os.readlink(path)}))


if __name__ == '__main__':
    unittest.main()
