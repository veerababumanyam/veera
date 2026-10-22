#!/usr/bin/env python3
"""Explicit identity disclosure for one submitted start command; no enrollment."""
import json
import os
import sys
import ownership


def handle(payload, host='claude'):
    command = '/veera:start' if host == 'claude' else '$veera-start'
    if not isinstance(payload, dict) or payload.get('prompt') != command or payload.get('hook_event_name') != 'UserPromptSubmit':
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
    context = {'veera_bootstrap': {'session_id': session_id, 'host': host, 'plugin_data': data, 'enrolled': False}}
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
