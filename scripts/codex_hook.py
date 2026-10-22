#!/usr/bin/env python3
"""Codex hook adapter: unsupported Claude ASK must become an explicit denial."""
import json
import os
import sys

os.environ['VEERA_HOST'] = 'codex'
import bootstrap
import ownership
import safety


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
                return result
        return {}
    elif tool not in ('Bash', 'Read', 'Glob', 'Grep', 'ToolSearch'):
        return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': 'Veera Codex adapter cannot safely classify this tool. Use native approval and an explicitly supported task-scoped operation; do not bypass this denial.'}}
    result = safety.handle(normalized)
    specific = result.get('hookSpecificOutput', {})
    if specific.get('permissionDecision') == 'ask':
        specific['permissionDecision'] = 'deny'
        specific['permissionDecisionReason'] = 'Human approval required outside this tool call; Codex hooks do not support ASK. ' + specific['permissionDecisionReason']
    return result


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        print('{}')
        return
    print(json.dumps(handle(payload)))


if __name__ == '__main__':
    main()
