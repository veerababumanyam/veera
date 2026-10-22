#!/usr/bin/env python3
"""Explicit identity disclosure for one submitted start command; no enrollment."""
import json
import os
import sys
from pathlib import Path
import ownership


def handle(payload, host='claude'):
    commands = ('/veera:start',) if host == 'claude' else ('$veera:start', '$veera-start')
    if not isinstance(payload, dict) or payload.get('prompt') not in commands or payload.get('hook_event_name') != 'UserPromptSubmit':
        return {}
    try:
        session_id = payload.get('session_id')
        ownership.session_key(session_id)
        data = os.environ.get('CLAUDE_PLUGIN_DATA')
        ownership.registry()  # Validate supported persistent location without writing.
        if not data:
            raise ValueError('Persistent data unavailable')
    except (ValueError, OSError):
        return {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': 'Veera bootstrap BLOCKED: actual session identity and host persistent plugin data are required. Do not invent them or enroll.'}}
    context = {'veera_bootstrap': {'session_id': session_id, 'host': host, 'plugin_data': data, 'package_root': str(Path(__file__).resolve().parents[1]), 'python_executable': sys.executable, 'cwd': payload.get('cwd'), 'enrolled': False}}
    if host == 'codex':
        policy_path = Path(__file__).resolve().parents[1] / 'docs/model-policy.json'
        context['veera_model_policy'] = json.loads(policy_path.read_text(encoding='utf-8'))
        context['veera_model_policy']['applied_to_current_model'] = False
    return {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': 'Actual host identity for this explicitly requested Veera start only. Preserve native permissions; this is not task/publication approval. Pass CLAUDE_PLUGIN_DATA and VEERA_HOST explicitly to controller commands if the shell does not inherit them.\n' + json.dumps(context)}}


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        print('{}')
        return
    print(json.dumps(handle(payload, os.environ.get('VEERA_HOST', 'claude'))))


if __name__ == '__main__':
    main()
