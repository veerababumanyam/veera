"""Permission regressions use disposable fixture storage, never live registries."""
import json
import os
from pathlib import Path
import stat
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery
import ownership


class StoragePermissionTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='veera-storage-fixture-'))).resolve()
        self.root = self.base / 'project'
        self.root.mkdir()
        self.registry = self.base / 'plugin-data' / 'veera-v1' / 'codex' / 'sessions'
        self.enterContext(patch.object(ownership, 'REGISTRY', self.registry))

    def acl(self, paths):
        # Read only the test's exact disposable paths. Never inspect host state.
        for path in paths:
            self.assertTrue(path.resolve().is_relative_to(self.base.resolve()))
        program = """
        $ErrorActionPreference = 'Stop'
        $paths = ConvertFrom-Json $env:VEERA_TEST_ACL_PATHS
        @($paths | ForEach-Object {
            $acl = Get-Acl -LiteralPath $_
            [pscustomobject]@{
                protected = $acl.AreAccessRulesProtected
                inherited = @($acl.Access | Where-Object IsInherited).Count
                sddl = $acl.Sddl
            }
        }) | ConvertTo-Json -Compress
        """
        shell = shutil.which('pwsh') or 'powershell.exe'
        result = subprocess.run([shell, '-NoProfile', '-Command', program],
                                env=dict(os.environ, VEERA_TEST_ACL_PATHS=json.dumps([str(p) for p in paths])),
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        return value if isinstance(value, list) else [value]

    def legacy(self):
        directory = delivery.storage(self.root)
        (directory / 'workspace.json').write_text(json.dumps({'id': 'fixture-workspace', 'session_id': 'fixture-migrate'}))
        legacy = self.base / (ownership.session_key('fixture-migrate') + '.json')
        legacy.write_text(json.dumps({'session_id': 'fixture-migrate', 'root': str(self.root),
                                      'workspace_id': 'fixture-workspace', 'capability': 'test-only'}))
        return legacy

    def create_storage(self):
        record = Path(ownership.enroll('fixture-enroll', self.root, 'fixture-workspace'))
        self.assertEqual(ownership.lookup('fixture-enroll')['root'], str(self.root))
        before = record.read_bytes()
        with self.assertRaises(ValueError):
            ownership.enroll('fixture-enroll', self.root, 'replacement')
        self.assertEqual(record.read_bytes(), before)
        directory = delivery.storage(self.root)
        delivery.save(directory, {'status': 'complete', 'contract': {}, 'contract_hash': delivery.digest({})})
        archived = Path(delivery.archive(self.root)['path'])
        self.assertTrue((archived / 'state.json').is_file())
        # Exercise migration's independent directory-creation path too.
        migrated_registry = self.base / 'migrated-sessions'
        legacy = self.legacy()
        with patch.object(ownership, 'REGISTRY', migrated_registry):
            result = ownership.migrate('fixture-migrate', self.root, legacy)
            self.assertEqual(ownership.authorize('fixture-migrate', self.root, result['capability_file'])['workspace_id'], 'fixture-workspace')
        self.assertTrue(legacy.is_file())
        return [self.registry, directory, archived.parent, archived, migrated_registry], record

    @unittest.skipUnless(os.name == 'nt', 'Windows ACL inheritance')
    def test_windows_enrollment_state_archive_and_migration_inherit_host_acl(self):
        paths, record = self.create_storage()
        for path, acl in zip([*paths, record], self.acl([*paths, record])):
            with self.subTest(path=str(path)):
                self.assertFalse(acl['protected'], 'Plugin must not replace inherited Windows access with a user-only DACL')
                self.assertGreater(acl['inherited'], 0)

    @unittest.skipUnless(os.name == 'posix', 'POSIX mode bits')
    def test_posix_storage_stays_private(self):
        paths, record = self.create_storage()
        for path in paths:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)

    def test_existing_storage_permissions_and_contents_are_unchanged(self):
        directory = self.root / '.veera'
        directory.mkdir()
        saved = directory / 'saved.txt'
        saved.write_text('preserved')
        before = self.acl([directory])[0]['sddl'] if os.name == 'nt' else stat.S_IMODE(directory.stat().st_mode)
        delivery.storage(self.root)
        after = self.acl([directory])[0]['sddl'] if os.name == 'nt' else stat.S_IMODE(directory.stat().st_mode)
        self.assertEqual(after, before)
        self.assertEqual(saved.read_text(), 'preserved')

    def test_enrollment_and_migration_propagate_directory_denials(self):
        legacy = self.legacy()
        before = legacy.read_bytes()
        mkdir = Path.mkdir
        attempts = []

        def denied(path, *args, **kwargs):
            if path == self.registry:
                attempts.append(path)
                raise PermissionError('fixture host denial')
            return mkdir(path, *args, **kwargs)

        with patch.object(Path, 'mkdir', denied):
            with self.assertRaisesRegex(PermissionError, 'fixture host denial'):
                ownership.enroll('fixture-enroll', self.root, 'fixture-workspace')
            with self.assertRaisesRegex(PermissionError, 'fixture host denial'):
                ownership.migrate('fixture-migrate', self.root, legacy)
        self.assertEqual(attempts, [self.registry, self.registry])
        self.assertFalse(self.registry.exists())
        self.assertEqual(legacy.read_bytes(), before)

    def test_record_write_denial_does_not_retry_or_redirect(self):
        self.registry.mkdir(parents=True)
        with patch.object(ownership.os, 'open', side_effect=PermissionError('fixture record denial')) as create:
            with self.assertRaisesRegex(PermissionError, 'fixture record denial'):
                ownership.enroll('fixture-enroll', self.root, 'fixture-workspace')
        create.assert_called_once()
        self.assertEqual(list(self.registry.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
