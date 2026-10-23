"""Regressions for desktop skill links, without enrolling a real session."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import bootstrap
import ownership


def link(action='start', version='0.2.5'):
    return f'[$veera:{action}](C:\\Users\\VeeraDesktop\\.codex\\plugins\\cache\\veera-plugins\\veera\\{version}\\adapters\\codex\\skills\\{action}\\SKILL.md)'


class BootstrapInvocationTests(unittest.TestCase):
    def test_reported_old_version_skill_link_is_recognized(self):
        self.assertEqual(bootstrap.invocation(link(), 'codex'), 'start')

    def test_current_package_links_spaces_aliases_and_task_arguments(self):
        for action in ('start', 'build', 'fix', 'dashboard'):
            path = Path(bootstrap.__file__).resolve().parents[1] / f'adapters/codex/skills/{action}/SKILL.md'
            tail = '' if action == 'start' else ' Investigate the issue\nThen run the checks.'
            values = [link(action) + tail, f'[$veera-{action}](<{path.as_posix()}>)' + tail,
                      link(action).replace('VeeraDesktop', 'User (QA)').replace('](', '](<').replace('SKILL.md)', 'SKILL.md>)') + tail,
                      link(action).replace('VeeraDesktop', 'User%20Name') + tail]
            for value in values:
                with self.subTest(value=value):
                    self.assertEqual(bootstrap.invocation(' \n' + value + '\n ', 'codex'), action)

    def test_quotes_unrelated_links_traversal_and_wrong_hosts_do_not_activate(self):
        for value in ('Explain ' + link(), '`' + link() + '`', '"' + link() + '"', '> ' + link(),
                      link().replace('[$', '![$'), link().replace('skills\\start', 'skills\\fix'),
                      '[$veera:start](https://example.invalid/SKILL.md)',
                      '[$veera:start](C:/unrelated/start/SKILL.md)',
                      link().replace('0.2.5', '../0.2.5'), link().replace('0.2.5', '%2e%2e/0.2.5'),
                      link()[:-1], link() + ' extra', '$veera:starter'):
            with self.subTest(value=value):
                self.assertIsNone(bootstrap.invocation(value, 'codex'))
        self.assertIsNone(bootstrap.invocation(link(), 'claude'))

    def test_hook_returns_current_package_identity_and_capabilities_for_old_link(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ownership, 'REGISTRY', None), patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA': directory, 'VEERA_HOST': 'codex'}):
            result = bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'session_id': 'fixture-only',
                                       'cwd': directory, 'prompt': link()}, 'codex')
            data = json.loads(result['hookSpecificOutput']['additionalContext'].split('\n', 1)[1])
            self.assertEqual(data['veera_bootstrap']['package_root'], str(Path(bootstrap.__file__).resolve().parents[1]))
            self.assertEqual(data['veera_bootstrap']['session_id'], 'fixture-only')
            self.assertEqual(data['veera_bootstrap']['requested_action'], 'start')
            self.assertTrue(data['veera_bootstrap']['package_version'])
            self.assertIn('veera_capabilities', data)
            self.assertFalse(data['veera_bootstrap']['enrolled'])
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_link_cannot_supply_or_replace_host_identity(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ownership, 'REGISTRY', None), patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA': directory, 'VEERA_HOST': 'codex'}):
            result = bootstrap.handle({'hook_event_name': 'UserPromptSubmit', 'prompt': link(), 'cwd': directory}, 'codex')
            self.assertIn('BLOCKED', result['hookSpecificOutput']['additionalContext'])
            self.assertEqual(list(Path(directory).iterdir()), [])
