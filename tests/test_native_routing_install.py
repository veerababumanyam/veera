from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import install_codex_routing as installer


class RoutingInstallTests(unittest.TestCase):
    def test_dangling_runtime_symlink_is_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory).resolve()
            runtime = home / 'veera-routing-runtime.json'
            self.assertFalse(runtime.exists())
            with patch.object(Path, 'is_symlink', autospec=True,
                              side_effect=lambda path: path == runtime):
                with self.assertRaisesRegex(ValueError, 'symlink runtime'):
                    installer.install(home)
            self.assertEqual(list(home.iterdir()), [])

    def test_preserves_settings_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            before = 'model = "parent-model"\n[agents.other]\ndescription = "keep"\n'
            (home / 'config.toml').write_text(before)
            first = installer.install(home)
            content = (home / 'config.toml').read_text()
            self.assertEqual(Path(first['config_backup']).read_text(), before)
            self.assertEqual(installer.install(home)['config_backup'], None)
            self.assertEqual((home / 'config.toml').read_text(), content)
            result = tomllib.loads(content)
            self.assertEqual(result['model'], 'parent-model')
            self.assertEqual(result['agents']['other']['description'], 'keep')
            self.assertEqual(set(result['agents']), {'other', 'veera_light', 'veera_important'})
            import json
            self.assertEqual(json.loads((home / 'veera-routing-runtime.json').read_text())['python_executable'], sys.executable)

    def test_conflicts_and_disabled_policy_make_no_changes(self):
        for before in ('[agents.veera_light]\ndescription="mine"\n', '[features]\nmulti_agent=false\n'):
            with tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                (home / 'config.toml').write_text(before)
                with self.assertRaises(ValueError):
                    installer.install(home)
                self.assertEqual((home / 'config.toml').read_text(), before)
                self.assertFalse((home / 'agents').exists())
