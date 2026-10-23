#!/usr/bin/env python3
"""Codex task guard; execution permissions belong to the host, not an ASK shim."""
import json
import os
import sys

import bootstrap
import ownership
import safety
from codex_compat import UNEXPECTED_ASK


def native_decision(result):
    """Every safety result, including patch targets, crosses this boundary."""
    specific = result.get('hookSpecificOutput', {})
    if specific.get('permissionDecision') == 'ask':
        return {'hookSpecificOutput': {
            **specific, 'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
            'permissionDecisionReason': UNEXPECTED_ASK + ' ' + specific.get('permissionDecisionReason', '')}}
    return result


def handle(payload):
    if not isinstance(payload, dict):
        return {}
    if payload.get('hook_event_name') == 'UserPromptSubmit':
        return bootstrap.handle(payload, 'codex')
    if payload.get('hook_event_name') != 'PreToolUse':
        return {}
    try:
        key = ownership.session_key(payload.get('session_id'))
        path = ownership.registry() / (key + '.json')
        if not path.exists() and not path.is_symlink():
            return {}
    except (ValueError, OSError):
        return {}
    if not isinstance(payload.get('tool_input'), dict):
        return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': 'Owned Codex tool input must be a valid object'}}
    tool = payload.get('tool_name')
    normalized = dict(payload)
    if tool in ('exec_command', 'shell_command'):
        raw = payload.get('tool_input', {})
        normalized['tool_name'] = 'Bash'
        normalized['tool_input'] = {'command': raw.get('cmd', raw.get('command', ''))}
    elif tool == 'apply_patch':
        patch = payload.get('tool_input', {}).get('command', '')
        if not isinstance(patch, str) or not patch.startswith('*** Begin Patch\n') or not patch.rstrip().endswith('*** End Patch'):
            return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': 'Unsupported patch envelope'}}
        targets = []
        for line in patch.splitlines():
            for prefix in ('*** Add File: ', '*** Update File: ', '*** Delete File: ', '*** Move to: '):
                if line.startswith(prefix):
                    targets.append(line[len(prefix):])
        if not targets:
            return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': 'Patch contains no verified file targets'}}
        for target in targets:
            result = safety.handle({**payload, 'tool_name': 'Write', 'tool_input': {'file_path': target}})
            if result:
                return native_decision(result)
        return {}
    # Other tools retain owner/cwd/terminal checks. Their execution permissions
    # remain with Codex; an unfamiliar name alone is not a reason to block work.
    return native_decision(safety.handle(normalized))


def main():
    # Set only in the actual hook child, never as a side effect of importing it.
    os.environ['VEERA_HOST'] = 'codex'
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        print('{}')
        return
    print(json.dumps(handle(payload)))


if __name__ == '__main__':
    main()
