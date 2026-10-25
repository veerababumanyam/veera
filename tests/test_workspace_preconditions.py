"""Workspace starts on ordinary repositories: any default branch name, tool output tolerated."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery as d
import git_delivery as g


class WorkspacePreconditionTests(unittest.TestCase):
    def repo(self, branch='master'):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.original = self.base / 'project'
        subprocess.run(['git', 'init', '-q', '-b', branch, str(self.original)], check=True)
        g.git(self.original, 'config', 'user.name', 'Fixture')
        g.git(self.original, 'config', 'user.email', 'fixture@example.invalid')
        # Isolate from the developer's global ignore rules.
        (self.base / 'no-excludes').write_text('')
        g.git(self.original, 'config', 'core.excludesFile', str(self.base / 'no-excludes'))
        (self.original / 'pkg').mkdir()
        (self.original / 'pkg' / 'core.py').write_text('value = 1\n')
        (self.original / '.gitignore').write_text('*.pyc\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-m', 'Fixture baseline')
        return g.git(self.original, 'rev-parse', 'HEAD')

    def start(self, task='fix'):
        return g.workspace(self.original, task)

    def test_master_default_branch_is_the_base(self):
        tip = self.repo('master')
        result = self.start()
        self.assertEqual((result['base'], result['base_branch']), (tip, 'master'))
        self.assertEqual(g.git(result['root'], 'rev-parse', 'HEAD'), tip)
        self.assertEqual(g.git(self.original, 'branch', '--show-current'), 'master')

    def test_trunk_and_detached_head_at_default_tip(self):
        tip = self.repo('trunk')
        g.git(self.original, 'switch', '--detach')
        result = self.start()
        self.assertEqual((result['base'], result['base_branch']), (tip, 'trunk'))

    def test_origin_head_names_the_default_among_several(self):
        self.repo('main')
        g.git(self.original, 'branch', 'master')
        g.git(self.original, 'switch', '-q', 'master')
        (self.original / 'pkg' / 'core.py').write_text('value = 2\n')
        g.git(self.original, 'commit', '-qam', 'Master moves on')
        remote = self.base / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(remote)], check=True)
        g.git(self.original, 'remote', 'add', 'origin', str(remote))
        g.git(self.original, 'push', '-q', 'origin', 'master', 'main')
        g.git(self.original, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/master')
        result = self.start()
        self.assertEqual(result['base_branch'], 'master')
        g.git(self.original, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/main')
        with self.assertRaisesRegex(d.DeliveryError, 'Start from main'):
            self.start('other')

    def test_topic_branch_off_master_still_refused(self):
        self.repo('master')
        g.git(self.original, 'switch', '-q', '-c', 'topic')
        (self.original / 'topic.py').write_text('unrelated\n')
        g.git(self.original, 'add', 'topic.py')
        g.git(self.original, 'commit', '-qm', 'Unrelated topic')
        with self.assertRaisesRegex(d.DeliveryError, 'Start from master'):
            self.start()

    def test_ambiguous_default_branch_refused(self):
        self.repo('dev')
        g.git(self.original, 'branch', 'release')
        with self.assertRaisesRegex(d.DeliveryError, 'default branch'):
            self.start()

    def test_untracked_code_index_folder_does_not_block(self):
        tip = self.repo('master')
        index = self.original / 'graft'
        index.mkdir()
        (index / 'graph.db').write_text('index')
        (self.original / '.claude').mkdir()
        (self.original / '.claude' / 'settings.local.json').write_text('{}')
        (self.original / 'pkg' / '.cache-tool').write_text('cache')
        result = self.start()
        self.assertEqual(result['base'], tip)
        self.assertEqual(sorted(result['left_in_original']), ['.claude/', 'graft/', 'pkg/.cache-tool'])
        self.assertEqual((index / 'graph.db').read_text(), 'index')
        self.assertFalse((Path(result['root']) / 'graft').exists())

    def test_untracked_agent_instruction_and_tags_files_do_not_block(self):
        self.repo('master')
        for name in ('CLAUDE.md', 'AGENTS.md', 'tags'):
            (self.original / name).write_text('tool output\n')
        result = self.start()
        self.assertEqual(sorted(result['left_in_original']), ['AGENTS.md', 'CLAUDE.md', 'tags'])
        self.assertFalse((Path(result['root']) / 'CLAUDE.md').exists())
        # The same names below the top level, or tracked and edited, are source.
        (self.original / 'pkg' / 'CLAUDE.md').write_text('peer notes\n')
        with self.assertRaisesRegex(d.DeliveryError, 'pkg/CLAUDE.md'):
            self.start('nested')
        (self.original / 'pkg' / 'CLAUDE.md').unlink()
        g.git(self.original, 'add', 'CLAUDE.md')
        g.git(self.original, 'commit', '-qm', 'Track instructions')
        (self.original / 'CLAUDE.md').write_text('edited\n')
        with self.assertRaisesRegex(d.DeliveryError, r'uncommitted changes.*: CLAUDE\.md$'):
            self.start('tracked')

    def test_appended_ignore_line_and_ignored_folder_do_not_block(self):
        self.repo('master')
        with open(self.original / '.gitignore', 'a') as handle:
            handle.write('.code-index/\n')
        (self.original / '.code-index').mkdir()
        (self.original / '.code-index' / 'symbols.json').write_text('{}')
        (self.original / 'pkg' / 'core.pyc').write_text('compiled')
        result = self.start()
        self.assertEqual(result['left_in_original'], ['.gitignore'])
        self.assertEqual((self.original / '.gitignore').read_text(), '*.pyc\n.code-index/\n')
        self.assertEqual((Path(result['root']) / '.gitignore').read_text(), '*.pyc\n')

    def test_rewritten_ignore_file_blocks(self):
        self.repo('master')
        (self.original / '.gitignore').write_text('*.log\n')
        with self.assertRaisesRegex(d.DeliveryError, r'uncommitted changes.*\.gitignore'):
            self.start()

    def test_modified_or_staged_source_and_loose_files_block(self):
        self.repo('master')
        cases = [
            lambda: (self.original / 'pkg' / 'core.py').write_text('value = 3\n'),
            lambda: ((self.original / 'pkg' / 'new.py').write_text('new\n'), g.git(self.original, 'add', 'pkg/new.py')),
            lambda: (self.original / 'notes.py').write_text('peer work\n'),
            lambda: (self.original / 'pkg' / 'helper.py').write_text('peer work\n'),
            lambda: g.git(self.original, 'rm', '-q', '--cached', 'pkg/core.py'),
        ]
        for index, make in enumerate(cases):
            with self.subTest(case=index):
                make()
                with self.assertRaisesRegex(d.DeliveryError, 'uncommitted changes'):
                    self.start('case-' + str(index))
                self.assertFalse((self.base / ('project-veera-case-' + str(index))).exists())
                g.git(self.original, 'reset', '-q', '--hard')
                g.git(self.original, 'clean', '-qfd')

    def test_task_worktree_with_tool_folder_passes_init_cleanliness(self):
        self.repo('master')
        result = self.start()
        root = Path(result['root'])
        (root / 'graft').mkdir()
        (root / 'graft' / 'graph.db').write_text('index')
        g.clean(root)
        (root / 'pkg' / 'core.py').write_text('value = 4\n')
        with self.assertRaises(d.DeliveryError):
            g.clean(root)

    def test_check_caches_in_scope_pass_init_and_verify_inputs(self):
        self.repo('master')
        root = Path(self.start()['root'])
        self.assertEqual(g.owned(root)['branch'], 'veera/fix')
        (g.common(root) / 'info').mkdir(exist_ok=True)
        (g.common(root) / 'info' / 'exclude').write_text('.pytest_cache/\n*.local\n')
        (root / 'pkg' / '__pycache__').mkdir()
        (root / 'pkg' / '__pycache__' / 'core.cpython-311.pyc').write_bytes(b'\0')
        (root / 'pkg' / 'stray.pyc').write_bytes(b'\0')
        (root / 'pkg' / '.pytest_cache').mkdir()
        (root / 'pkg' / '.pytest_cache' / 'README.md').write_text('cache')
        g.validate_inputs(root, ['pkg'])
        g.clean(root)
        (root / 'pkg' / 'settings.local').write_text('secret = 1\n')
        with self.assertRaisesRegex(d.DeliveryError, 'settings.local'):
            g.validate_inputs(root, ['pkg'])

    def test_finished_foreign_task_and_plain_folder_are_skipped_untouched(self):
        tip = self.repo('master')
        first = Path(self.start()['root'])
        metadata = d.read_json(first / '.veera' / 'workspace.json')
        d.atomic(first / '.veera' / 'workspace.json', {**metadata, 'session_id': 'earlier-owner'})
        (first / '.veera' / 'state.json').write_text('{"status": "verified-local"}')
        (self.base / 'project-veera-fix-2').mkdir()
        (self.base / 'project-veera-fix-2' / 'notes.txt').write_text('not a task')
        result = self.start()
        self.assertEqual((Path(result['root']), result['branch'], result['base']), ((self.base / 'project-veera-fix-3').resolve(), 'veera/fix-3', tip))
        self.assertEqual((first / '.veera' / 'state.json').read_text(), '{"status": "verified-local"}')
        self.assertEqual(sorted(p.name for p in (self.base / 'project-veera-fix-2').iterdir()), ['notes.txt'])

    def test_leftover_branch_without_folder_is_skipped(self):
        self.repo('master')
        g.git(self.original, 'branch', 'veera/fix')
        result = self.start()
        self.assertEqual(result['branch'], 'veera/fix-2')

    def test_partial_foreign_workspace_still_refuses(self):
        self.repo('master')
        first = Path(self.start()['root'])
        metadata = d.read_json(first / '.veera' / 'workspace.json')
        d.atomic(first / '.veera' / 'workspace.json', {**metadata, 'session_id': 'other-owner'})
        with self.assertRaisesRegex(d.DeliveryError, 'session owner'):
            self.start()
        self.assertFalse((self.base / 'project-veera-fix-2').exists())

    def generated_layout(self):
        self.repo('master')
        (self.original / 'src' / 'pkg').mkdir(parents=True)
        (self.original / 'src' / 'pkg' / '__init__.py').write_text('')
        (self.original / '.gitignore').write_text('*.pyc\n__pycache__/\nsrc/pkg/_version.py\n*.so\nbuild/\n*.log\n.env\ncoverage.xml\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-qm', 'Source layout')
        package = self.original / 'src' / 'pkg'
        (package / '_version.py').write_text('version = "1.0"\n')
        (package / '_speedups.so').write_bytes(b'\x7fELF')
        (package / 'run.log').write_text('noise')
        (package / '.env').write_text('TOKEN=1\n')
        (package / '__pycache__').mkdir()
        (package / '__pycache__' / 'core.cpython-311.pyc').write_bytes(b'\0')
        (self.original / 'build' / 'lib').mkdir(parents=True)
        (self.original / 'build' / 'lib' / 'pkg.py').write_text('built\n')
        (self.original / 'coverage.xml').write_text('<coverage/>')
        (self.original / '.env').write_text('TOKEN=2\n')

    def test_generated_files_beside_source_are_carried_into_the_task(self):
        self.generated_layout()
        result = self.start()
        root = Path(result['root'])
        self.assertEqual(result['carried'], ['src/pkg/_speedups.so', 'src/pkg/_version.py'])
        self.assertEqual(d.read_json(root / '.veera' / 'workspace.json')['carried'], result['carried'])
        self.assertEqual((root / 'src' / 'pkg' / '_version.py').read_text(), 'version = "1.0"\n')
        self.assertEqual((root / 'src' / 'pkg' / '_speedups.so').read_bytes(), b'\x7fELF')
        for name in ('src/pkg/run.log', 'src/pkg/.env', 'src/pkg/__pycache__', 'build', 'coverage.xml', '.env'):
            self.assertFalse((root / name).exists(), name)
        self.assertEqual((self.original / 'src' / 'pkg' / '_version.py').read_text(), 'version = "1.0"\n')
        g.clean(root)
        g.validate_inputs(root, ['src'])
        (root / 'src' / 'pkg' / '_local.so').write_bytes(b'new')
        with self.assertRaisesRegex(d.DeliveryError, '_local.so'):
            g.validate_inputs(root, ['src'])

    def test_install_written_version_module_lets_worktree_tests_import(self):
        # Shaped like pytest-dev/pytest: setuptools-scm writes an ignored
        # src/_pytest/_version.py at install time and the package imports it.
        self.repo('master')
        package = self.original / 'src' / '_pytest'
        package.mkdir(parents=True)
        (package / '__init__.py').write_text('from ._version import version as __version__\n')
        (self.original / 'testing').mkdir()
        (self.original / 'testing' / 'test_core.py').write_text('import _pytest\n')
        with open(self.original / '.gitignore', 'a') as handle:
            handle.write('src/_pytest/_version.py\n.eggs/\n*.egg-info/\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-qm', 'Package')
        (package / '_version.py').write_text("version = '4.5.1.dev3'\n")
        (self.original / 'src' / 'pytest.egg-info').mkdir()
        (self.original / 'src' / 'pytest.egg-info' / 'PKG-INFO').write_text('Name: pytest\n')
        result = self.start()
        root = Path(result['root'])
        self.assertEqual((result['carried'], result['carry_skipped']), (['src/_pytest/_version.py'], []))
        self.assertFalse((root / 'src' / 'pytest.egg-info').exists())
        probe = subprocess.run([sys.executable, '-c', 'import _pytest; print(_pytest.__version__)'], cwd=root, env={**os.environ, 'PYTHONPATH': str(root / 'src')}, capture_output=True, text=True)
        self.assertEqual((probe.returncode, probe.stdout.strip()), (0, '4.5.1.dev3'), probe.stderr)
        self.assertEqual(g.git(root, 'status', '--porcelain', '--', '.', ':(exclude).veera'), '')
        g.clean(root)
        g.validate_inputs(root, ['src/_pytest', 'testing'])

    def test_failed_copy_is_reported_and_never_aborts_the_start(self):
        self.generated_layout()
        real = g.shutil.copy2

        def copy(source, destination):
            if Path(source).name == '_speedups.so':
                raise PermissionError('locked by a running process')
            return real(source, destination)

        with mock.patch.object(g.shutil, 'copy2', copy):
            result = self.start()
        root = Path(result['root'])
        self.assertEqual((result['carried'], result['carry_skipped']), (['src/pkg/_version.py'], ['src/pkg/_speedups.so']))
        self.assertTrue((root / '.veera' / 'workspace.json').is_file())
        self.assertFalse((root / 'src' / 'pkg' / '_speedups.so').exists())

    def test_carry_is_bounded_and_unreadable_metadata_exempts_nothing(self):
        self.generated_layout()
        with mock.patch.object(g, 'CARRY_FILE_BYTES', 8), mock.patch.object(g, 'CARRY_FILES', 1):
            result = self.start()
        root = Path(result['root'])
        self.assertEqual(result['carried'], ['src/pkg/_speedups.so'])
        self.assertEqual(result['carry_skipped'], ['src/pkg/_version.py'])
        self.assertNotIn('carry_skipped', d.read_json(root / '.veera' / 'workspace.json'))
        self.assertFalse((root / 'src' / 'pkg' / '_version.py').exists())
        metadata = d.read_json(root / '.veera' / 'workspace.json')
        d.atomic(root / '.veera' / 'workspace.json', {**metadata, 'carried': 'src/pkg/_speedups.so'})
        with self.assertRaisesRegex(d.DeliveryError, '_speedups.so'):
            g.validate_inputs(root, ['src'])

    def test_generated_python_module_is_carried_before_other_files(self):
        self.generated_layout()
        catalogs = self.original / 'src' / 'pkg' / 'locale'
        catalogs.mkdir()
        (catalogs / 'messages.po').write_text('msgid ""\n')
        with open(self.original / '.gitignore', 'a') as handle:
            handle.write('*.mo\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-qm', 'Catalogs')
        for index in range(3):
            (catalogs / ('a' + str(index) + '.mo')).write_bytes(b'\0')
        with mock.patch.object(g, 'CARRY_FILES', 1):
            result = self.start()
        root = Path(result['root'])
        self.assertEqual(result['carried'], ['src/pkg/_version.py'])
        self.assertEqual((root / 'src' / 'pkg' / '_version.py').read_text(), 'version = "1.0"\n')
        self.assertFalse((root / 'src' / 'pkg' / '_speedups.so').exists())
        self.assertFalse((root / 'src' / 'pkg' / 'locale' / 'a0.mo').exists())
        # Without the cap every catalog beside tracked source comes along.
        everything = self.start('all')
        self.assertEqual(everything['carried'], ['src/pkg/_speedups.so', 'src/pkg/_version.py', 'src/pkg/locale/a0.mo', 'src/pkg/locale/a1.mo', 'src/pkg/locale/a2.mo'])
        self.assertEqual(everything['carried_count'], 5)

    def test_long_carry_is_reported_briefly_but_exempted_in_full(self):
        self.generated_layout()
        catalogs = self.original / 'src' / 'pkg' / 'locale'
        catalogs.mkdir()
        (catalogs / 'messages.po').write_text('msgid ""\n')
        with open(self.original / '.gitignore', 'a') as handle:
            handle.write('*.mo\n')
        g.git(self.original, 'add', '.')
        g.git(self.original, 'commit', '-qm', 'Catalogs')
        for index in range(30):
            (catalogs / ('a%02d.mo' % index)).write_bytes(b'\0')
        result = self.start()
        root = Path(result['root'])
        stored = d.read_json(root / '.veera' / 'workspace.json')['carried']
        self.assertEqual((len(result['carried']), result['carried_count'], len(stored)), (20, 32, 32))
        self.assertEqual(result['carried'], stored[:20])
        g.validate_inputs(root, ['src'])

    def test_result_names_the_task_root_for_every_later_command(self):
        self.repo('master')
        result = self.start()
        self.assertIn('cd "' + result['root'] + '" &&', result['next'])
        self.assertEqual(result['carried_count'], 0)
        self.assertNotIn('next', d.read_json(Path(result['root']) / '.veera' / 'workspace.json'))


if __name__ == '__main__':
    unittest.main()
