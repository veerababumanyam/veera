#!/usr/bin/env python3
"""Automatic Sol/Astra selection for Codex delegates and DeepSeek pro/flash for DSH.

Claude uses the Codex bridge, never OpenAI IDs in Claude frontmatter. DeepSeek
Harness routes to deepseek-v4-pro (important) or deepseek-flash (light), both at
high reasoning effort, and dispatches a native subagent with the selected route
when the host subagent model selection setting is enabled.
No owner adoption, capability transfer, permission bypass or model fallback.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RISK = re.compile(r'\b(secur\w*|permission\w*|auth\w*|migrat\w*|concurren\w*|ownership|'
                  r'production|deploy\w*|architecture|kernel\w*|inference|benchmark\w*|'
                  r'diagnos\w*|root.cause|release|review|data.loss|billing|credential\w*|'
                  r'payment\w*|encrypt\w*|key\w*|rollback|design|decide|implement|optimi[sz]e|'
                  r'delete|remove|replace|modify|rewrite|fix|write|then|also|and)\b', re.I)
ROUTINE = re.compile(r'\s*(?:(?:summari[sz]e|explain) (?:README|[\w./\\-]+\.(?:md|txt))|'
                     r'(?:list|find) files(?: in [\w./\\-]+)?|format markdown|'
                     r'run established checks)\s*', re.I)


def select(task, host='codex'):
    if not isinstance(task, str) or not task.strip():
        raise ValueError('A nonempty bounded task is required')
    policy = json.loads((ROOT / 'docs/model-policy.json').read_text(encoding='utf-8'))
    table = policy['dsh'] if host == 'dsh' else policy
    risk = RISK.search(task)
    tier = 'important' if risk or not ROUTINE.fullmatch(task) else 'light'
    selection = {'tier': tier, 'model': table[tier]['model'],
                 'reasoning_effort': table[tier]['reasoning_effort'],
                 'reason': ('Consequential work: ' + risk.group(0)) if risk else
                           ('Recognized routine task' if tier == 'light' else 'Uncertain task; conservative escalation')}
    if host == 'dsh':
        selection['provider'] = table.get('provider', 'deepseek-official')
    return selection


def native_plan(task, cwd, selection=None):
    selection = selection or select(task, 'codex')
    return {'calling_host': 'codex', 'execution_host': 'codex', 'selection': selection,
            'status': 'dispatch_required', 'actual_model_verified': False,
            'dispatch': {'tool': 'spawn_agent', 'agent_type': 'veera_' + selection['tier'],
                         'fork_context': False,
                         'message': 'Bounded findings-only task. Do not edit, delegate, invoke Veera workflows, '
                                    'access credentials or other sessions, or call mutating connectors. '
                                    'Use this authorized source directory for relative source paths: '
                                    + json.dumps(str(cwd)) + '. Do not assume your inherited cwd is this directory. '
                                    'Return findings to the parent. Task:\n' + task},
            'confinement': 'Native subagent inherits parent sandbox, approvals and tools; findings-only instruction is cooperative'}


def dsh_plan(task, cwd, selection):
    return {'calling_host': 'dsh', 'execution_host': 'dsh', 'selection': selection,
            'status': 'dispatch_required', 'actual_model_verified': False,
            'dispatch': {'tool': 'subagent',
                         'provider': selection['provider'],
                         'model': selection['model'],
                         'reasoning_effort': selection['reasoning_effort'],
                         'fork_context': False,
                         'message': 'Bounded findings-only task. Do not edit, delegate, invoke Veera workflows, access credentials or other sessions, or call mutating connectors. Use this authorized source directory for relative source paths: ' + json.dumps(str(cwd)) + '. Do not assume your inherited cwd is this directory. Return findings to the parent. Task:\n' + task},
            'confinement': 'Native subagent inherits parent sandbox, approvals and tools; findings-only instruction is cooperative'}


def command(executable, cwd, selection):
    return [executable, '--no-daemon', '-C', str(cwd), '-s', 'read-only', '-a', 'never',
            'exec', '--skip-git-repo-check', '-m', selection['model'],
            '-c', 'model_reasoning_effort=' + json.dumps(selection['reasoning_effort']), '--json', '-']


def find_codex():
    if os.name == 'nt':
        shim = shutil.which('codex.cmd')
        if shim:
            vendor = Path(shim).parent / 'node_modules/@openai/codex/node_modules/@openai'
            candidates = list(vendor.glob('codex-win32-*/vendor/*/bin/codex.exe'))
            if len(candidates) == 1:
                return str(candidates[0])
        return shutil.which('codex.exe')
    return shutil.which('codex')


def verified_model(thread_id, expected):
    """Read only the exact session created by this invocation, never other owners."""
    if not isinstance(thread_id, str) or not re.fullmatch(r'[a-f0-9-]{36}', thread_id):
        return False
    home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    matches = list((home / 'sessions').glob('*/*/*/*-' + thread_id + '.jsonl'))
    if len(matches) != 1:
        return False
    actual = None
    try:
        for line in matches[0].read_text(encoding='utf-8').splitlines():
            event = json.loads(line)
            if event.get('type') == 'turn_context':
                actual = event.get('payload', {}).get('model')
    except (OSError, ValueError):
        return False
    return actual == expected


def execute(task, cwd, host, executable=None, timeout=300):
    if os.environ.get('VEERA_ROUTER_ACTIVE'):
        raise ValueError('Recursive model routing is forbidden')
    if host not in ('claude', 'codex', 'dsh'):
        raise ValueError('Unsupported calling host')
    cwd = Path(cwd).resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError('Working directory is required')
    selection = select(task, host)
    if host == 'dsh':
        return dsh_plan(task, cwd, selection)
    if host == 'codex':
        return native_plan(task, cwd, selection)
    executable = executable or find_codex()
    if not executable:
        raise ValueError('Packaged Codex CLI is required, including when called from Claude')
    env = dict(os.environ, VEERA_ROUTER_ACTIVE='1')
    # Never pass a parent owner capability or bootstrap identity to this fresh delegate.
    for key in list(env):
        if key.startswith('VEERA_') and key != 'VEERA_ROUTER_ACTIVE':
            env.pop(key)
    prompt = ('You are a bounded read-only Veera delegate. Do not delegate or invoke Veera workflows. '
              'Do not inspect other sessions, credentials or private plugin data. '
              'Return findings only; the parent retains all decisions and writes. Task:\n' + task)
    result = {'calling_host': host, 'execution_host': 'codex', 'selection': selection,
              'confinement': 'Native read-only file sandbox; external tool read-only behavior is cooperative under inherited host policy',
              'status': 'failed', 'actual_model_verified': False, 'response': ''}
    try:
        process = subprocess.run(command(executable, cwd, selection), input=prompt, text=True,
                                 encoding='utf-8', errors='replace', capture_output=True,
                                 timeout=timeout, env=env, shell=False)
    except subprocess.TimeoutExpired:
        result['error'] = 'Delegate timed out; no retry or fallback was attempted'
        return result
    completed = False
    for line in process.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'thread.started':
            result['thread_id'] = event.get('thread_id')
        if event.get('type') == 'item.completed' and event.get('item', {}).get('type') == 'agent_message':
            result['response'] += event['item'].get('text', '') + '\n'
        if event.get('type') in ('error', 'turn.failed'):
            result['error'] = 'Codex reported a delegate failure'
        completed |= event.get('type') == 'turn.completed'
    if process.returncode == 0 and completed and 'error' not in result:
        result['status'] = 'completed'
        result['actual_model_verified'] = verified_model(result.get('thread_id'), selection['model'])
    else:
        result.setdefault('error', 'Codex failed; inspect its native diagnostics. No fallback attempted.')
    result['response'] = result['response'].strip()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task-file', type=Path, required=True, help='UTF-8 bounded brief; never owner capabilities')
    parser.add_argument('--cwd', type=Path, required=True)
    parser.add_argument('--host', choices=['claude', 'codex', 'dsh'], required=True)
    parser.add_argument('--plan', action='store_true', help='Classify without running a model')
    args = parser.parse_args()
    try:
        task = args.task_file.read_text(encoding='utf-8-sig')
        result = select(task, args.host) if args.plan else execute(task, args.cwd, args.host)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if args.plan or result['status'] in ('completed', 'dispatch_required') else 1
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
