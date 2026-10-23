#!/usr/bin/env python3
"""Task-entry identity disclosure through the host hook; no enrollment."""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote
import ownership


def skill_link_command(prompt):
    """Unwrap a leading Codex skill chip; never read or execute its target."""
    match = re.match(r'^\[(\$veera[:-](start|build|fix|dashboard))\]\(', prompt)
    if not match:
        return prompt
    start = match.end()
    depth = 1
    end = None
    for index in range(start, min(len(prompt), start + 4096)):
        if prompt[index] in '\r\n':
            return prompt
        if prompt[index] == '(':
            depth += 1
        elif prompt[index] == ')':
            depth -= 1
            if not depth:
                end = index
                break
    if end is None:
        return prompt
    target = prompt[start:end]
    if target.startswith('<') and target.endswith('>'):
        target = target[1:-1]
    target = re.sub('/+', '/', unquote(target).replace('\\', '/'))
    if any(part in ('.', '..') for part in target.split('/')):
        return prompt
    suffix = f'adapters/codex/skills/{match[2]}/SKILL.md'
    current = (Path(__file__).resolve().parents[1] / suffix).as_posix()
    # Old installed links are invocation hints, not paths to load. The running
    # trusted hook always supplies its own current package and actual host ID.
    cached = re.fullmatch(r'(?:[A-Za-z]:)?/(?:[^/]+/)*\.codex/plugins/cache/veera-plugins/veera/'
                         r'\d+\.\d+\.\d+(?:[-+][\w.-]+)?/' + re.escape(suffix), target, re.I)
    if target.casefold() != current.casefold() and not cached:
        return prompt
    return match[1] + prompt[end + 1:]


def invocation(prompt, host):
    if not isinstance(prompt, str) or host not in ('claude', 'codex'):
        return None
    if host == 'codex':
        prompt = skill_link_command(prompt.strip())
    starts = ('/veera:start',) if host == 'claude' else ('$veera:start', '$veera-start')
    if prompt in starts:
        return 'start'
    prefix = r'/veera:' if host == 'claude' else r'\$veera[:-]'
    match = re.fullmatch(prefix + r'(build|fix|dashboard)(?:\s+[\s\S]*)?', prompt)
    return match[1] if match else None


def handle(payload, host='claude'):
    if not isinstance(payload, dict) or payload.get('hook_event_name') != 'UserPromptSubmit':
        return {}
    action = invocation(payload.get('prompt'), host)
    if not action:
        prompt = payload.get('prompt')
        # The coordinator understands intent and conversation history. A verb
        # whitelist here misses short requests, continuations and other languages.
        if (host not in ('claude', 'codex') or not isinstance(prompt, str) or not prompt.strip()
                or prompt.lstrip().startswith(('/', '$', '[', '>', '`', '"', "'", '<'))
                or os.environ.get('VEERA_ROUTER_ACTIVE')):
            return {}
        action = 'auto'
    return context(payload, host, action)


def tool_context(payload, host):
    """Recover context on a real skill read when no user-prompt event was sent.

    Tool-created desktop chats can begin with delegated input. This uses the
    actual PreToolUse identity; it neither simulates a prompt nor approves a tool.
    Call only for an unbound session, after existing guard classification.
    """
    if (not isinstance(payload, dict) or payload.get('hook_event_name') != 'PreToolUse'
            or host not in ('claude', 'codex') or os.environ.get('VEERA_ROUTER_ACTIVE')):
        return {}
    args = payload.get('tool_input')
    if not isinstance(args, dict):
        return {}
    tool = payload.get('tool_name')
    if tool == 'Read':
        value = args.get('file_path')
    elif tool in ('Bash', 'exec_command', 'shell_command'):
        value = args.get('cmd', args.get('command'))
        if not isinstance(value, str) or not re.search(r'(?:^|[\s;])(?:Get-Content|cat|type)\s', value, re.I):
            return {}
    elif tool == 'Skill' and args.get('skill') in ('veera:build', 'veera:fix'):
        return context(payload, host, 'auto')
    else:
        return {}
    if not isinstance(value, str):
        return {}
    value = re.sub('/+', '/', value.replace('\\', '/')).casefold()
    root = Path(__file__).resolve().parents[1]
    skills = root / ('adapters/codex/skills' if host == 'codex' else 'skills')
    for action in ('build', 'fix'):
        target = (skills / action / 'SKILL.md').as_posix().casefold()
        if (tool == 'Read' and value == target) or (tool != 'Read' and re.search(
                r'(?:^|[\s\'\"])' + re.escape(target) + r'(?=$|[\s\'\"])', value)):
            return context(payload, host, 'auto')
    return {}


def context(payload, host, action):
    """Disclose only actual hook inputs. Context does not enroll or grant authority."""
    event = payload['hook_event_name']
    try:
        session_id = payload.get('session_id')
        ownership.session_key(session_id)
        data = os.environ.get('CLAUDE_PLUGIN_DATA')
        ownership.registry()  # Validate supported persistent location without writing.
        if not data:
            raise ValueError('Persistent data unavailable')
    except (ValueError, OSError):
        message = ('Veera automatic identity is unavailable. Answer informational requests normally. '
                   'Owned delivery requires actual host session identity and persistent plugin data; '
                   'diagnose the host integration with ordinary permitted tools, without asking for a start command. '
                   'Do not invent identity or enroll.') if action == 'auto' else (
                   'Veera bootstrap BLOCKED: actual session identity and host persistent plugin data are required. Do not invent them or enroll.')
        return {'hookSpecificOutput': {'hookEventName': event, 'additionalContext': message}}
    package = Path(__file__).resolve().parents[1]
    manifest = package / ('.codex-plugin/plugin.json' if host == 'codex' else '.claude-plugin/plugin.json')
    try:
        version = json.loads(manifest.read_text(encoding='utf-8')).get('version')
    except (OSError, ValueError, AttributeError):
        version = None
    context = {'veera_bootstrap': {'session_id': session_id, 'host': host, 'plugin_data': data, 'package_root': str(package), 'package_version': version, 'python_executable': sys.executable, 'cwd': payload.get('cwd'), 'enrolled': False, 'requested_action': action,
                                  'activation': 'automatic' if action == 'auto' else 'explicit', 'identity_event': event,
                                  'routing_guide': str(package / 'docs/automatic-entry.md')}}
    if host == 'codex':
        from codex_compat import capabilities
        context['veera_capabilities'] = capabilities()
        policy_path = Path(__file__).resolve().parents[1] / 'docs/model-policy.json'
        context['veera_model_policy'] = json.loads(policy_path.read_text(encoding='utf-8'))
        context['veera_model_policy']['applied_to_current_model'] = False
    guidance = ('Veera is ready for automatic task routing. For an actionable software task, the user-facing coordinator '
                'reads routing_guide below and uses the matching Build/Fix skill now; no command or activation question. '
                'Use conversation context, not a keyword test. Questions, quoted requests, explicit opt-outs and '
                'findings-only delegates must not enroll or start delivery. Continue an existing owned task instead of '
                'starting another. Default new work to local-verify unless publication was requested. '
                'Veera maintenance uses ordinary host tools, not its own delivery workflow. ') if action == 'auto' else (
                'Actual host identity for this Veera invocation. Continue the authorized task in this turn; '
                'no separate start message. Start is an optional identity diagnostic. ')
    return {'hookSpecificOutput': {'hookEventName': event, 'additionalContext': guidance +
            'Identity disclosure is not enrollment, permission or publication approval. Preserve native permissions. '
            'Pass the returned plugin_data as CLAUDE_PLUGIN_DATA and host as VEERA_HOST to controller children.\n' + json.dumps(context)}}


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        print('{}')
        return
    print(json.dumps(handle(payload, os.environ.get('VEERA_HOST', 'claude'))))


if __name__ == '__main__':
    main()
