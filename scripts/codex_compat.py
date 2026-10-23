#!/usr/bin/env python3
"""Read-only package diagnostics, independent of Veera ownership and delivery."""
import argparse
import json
from pathlib import Path
import sys

UNEXPECTED_ASK = 'Unexpected legacy ASK from the Codex adapter. Use matching adapter/runtime versions; no unsupported decision is emitted.'
POLICY_GUIDANCE = ('Veera adds no interactive approval gate on Codex. Use the existing host permission policy '
                   'and recorded upfront user authorization. Controller ownership, frozen scope, '
                   'state and evidence checks remain in force. Host denials remain binding.')


def capabilities():
    return {
        'hook_ask': False,
        'extra_approval_gate': False,
        'authority_recovery': {'amend': 'controller-validated', 'resume': 'controller-validated', 'extend-repairs': 'controller-validated', 'correct-check-reporting': 'controller-validated', 'rebind-check-inputs': 'controller-validated', 'blocker-human-resolve': 'controller-validated'},
        'arbitrary_shell': 'host-policy',
        'canonical_bash_execution_cwd': 'not-exposed-by-host',
        'unknown_mutating_tools': 'host-policy',
        'native_approval_and_sandbox': 'unchanged',
        'live_host_verified': False,
    }


def diagnose(root):
    """Read this package only; no session lookup, subprocesses, or file writes."""
    root = Path(root).resolve()
    errors = []
    version = None
    try:
        manifest = json.loads((root / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
        version = manifest['version']
        for field in ('skills', 'hooks'):
            target = (root / manifest[field]).resolve()
            if not target.is_relative_to(root) or not target.exists():
                errors.append('Missing or external manifest target: ' + field)
            elif field == 'hooks':
                hooks = json.loads(target.read_text(encoding='utf-8'))['hooks']
                for event in ('UserPromptSubmit', 'PreToolUse'):
                    groups = hooks.get(event)
                    if not isinstance(groups, list) or not groups or not all(
                            isinstance(group, dict) and isinstance(group.get('hooks'), list)
                            and group['hooks'] and all(isinstance(hook, dict)
                                and hook.get('type') == 'command' and isinstance(hook.get('command'), str)
                                and hook['command'].strip() for hook in group['hooks']) for group in groups):
                        errors.append('Missing or invalid command hooks: ' + event)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        errors.append('Invalid or missing Codex manifest/hooks')
    for relative in ('scripts/codex_hook.py', 'scripts/bootstrap.py', 'scripts/safety.py',
                     'scripts/ownership.py', 'docs/model-policy.json'):
        if not (root / relative).is_file():
            errors.append('Missing package file: ' + relative)
    if sys.version_info < (3, 12):
        errors.append('Python 3.12 or newer is required')
    return {'package_root': str(root), 'version': version, 'python_executable': sys.executable,
            'package_status': 'invalid' if errors else 'files-present', 'errors': errors,
            'capabilities': capabilities(), 'activation': 'not-verified',
            'guidance': POLICY_GUIDANCE}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host-status', action='store_true', help='Read native hook metadata without starting a chat or modifying trust')
    parser.add_argument('--cwd', type=Path, default=Path.cwd(), help='Authorized project for the optional host metadata query')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = diagnose(root)
    if args.host_status:
        from codex_host import inspect
        report['host_hooks'] = inspect(root, args.cwd)
    print(json.dumps(report, indent=2))
    sys.exit(1 if report['errors'] else 0)
