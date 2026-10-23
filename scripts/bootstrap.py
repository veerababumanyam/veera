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
    package = Path(__file__).resolve().parents[1]
    manifest = package / ('.codex-plugin/plugin.json' if host == 'codex' else '.claude-plugin/plugin.json')
    try:
        version = json.loads(manifest.read_text(encoding='utf-8')).get('version')
    except (OSError, ValueError, AttributeError):
        version = None
    context = {'veera_bootstrap': {'session_id': session_id, 'host': host, 'plugin_data': data, 'package_root': str(package), 'package_version': version, 'python_executable': sys.executable, 'cwd': payload.get('cwd'), 'enrolled': False, 'requested_action': action}}
    if host == 'codex':
        from codex_compat import capabilities
        context['veera_capabilities'] = capabilities()
        policy_path = Path(__file__).resolve().parents[1] / 'docs/model-policy.json'
        context['veera_model_policy'] = json.loads(policy_path.read_text(encoding='utf-8'))
        context['veera_model_policy']['applied_to_current_model'] = False
    return {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': 'Actual host identity for this direct Veera invocation. Build/Fix may continue the authorized task in this same turn without a separate start message. Start is an optional identity diagnostic. Preserve native permissions; identity disclosure is not enrollment or publication approval. Pass CLAUDE_PLUGIN_DATA and VEERA_HOST explicitly to controller commands if the shell does not inherit them.\n' + json.dumps(context)}}


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        print('{}')
        return
    print(json.dumps(handle(payload, os.environ.get('VEERA_HOST', 'claude'))))


if __name__ == '__main__':
    main()
