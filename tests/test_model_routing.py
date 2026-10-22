import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import bootstrap
import ownership


class ModelRoutingTests(unittest.TestCase):
    def test_codex_bootstrap_delivers_policy_without_claiming_switch(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ownership, 'REGISTRY', None), patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA':directory,'VEERA_HOST':'codex'}):
            response = bootstrap.handle({'hook_event_name':'UserPromptSubmit','prompt':'$veera:start','session_id':'fixture-only'}, 'codex')
            data = json.loads(response['hookSpecificOutput']['additionalContext'].split('\n',1)[1])
            policy = data['veera_model_policy']
            self.assertEqual(policy['light']['model'],'gpt-6.1-sol')
            self.assertEqual(policy['important']['model'],'gpt-6-astra')
            self.assertFalse(policy['applied_to_current_model'])
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_claude_bootstrap_does_not_apply_openai_routing(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ownership, 'REGISTRY', None), patch.dict(os.environ, {'CLAUDE_PLUGIN_DATA':directory,'VEERA_HOST':'claude'}):
            response = bootstrap.handle({'hook_event_name':'UserPromptSubmit','prompt':'/veera:start','session_id':'fixture-only'}, 'claude')
            data = json.loads(response['hookSpecificOutput']['additionalContext'].split('\n',1)[1])
            self.assertNotIn('veera_model_policy',data)
