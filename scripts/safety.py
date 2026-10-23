#!/usr/bin/env python3
"""Defense-in-depth hook, not an OS sandbox or a shell authorization parser."""
import json
import os
from pathlib import Path
import re
import shlex
import sys
import ownership
STATE = '.veera'
TERMINAL = {'complete', 'verified-local', 'blocked', 'budget-exhausted', 'user-stopped'}


def shell_words(command):
    lexer = shlex.shlex(command, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    if os.name == 'nt':
        lexer.escape = ''  # PowerShell/Windows paths use literal backslashes.
    words = list(lexer)
    # Canonicalize only the known controller path; preserve every other token.
    controller = Path(__file__).resolve().parent / 'delivery.py'
    if len(words) > 1 and Path(words[1]).resolve() == controller:
        words[1] = str(controller)
    return words


def status(root):
    from delivery import status as implementation
    return implementation(root)


def controller_command(words):
    return (len(words) >= 3 and words[1] == str(Path(__file__).resolve().parent / 'delivery.py')
            and (words[0] == 'python3' or Path(words[0]).resolve() == Path(sys.executable).resolve()))


def scoped(name, scope):
    from delivery import scoped as implementation
    return implementation(name, scope)

READ_ONLY = {'Read', 'Glob', 'Grep', 'ToolSearch', 'ListAgents'}
DANGEROUS = re.compile(r'(?:\bgit\s+(?:push|reset\s+--hard|clean\s+-)|\brm\s+[^\n]*-[a-zA-Z]*[rf]|\bsudo\b|\bcurl\b.*\|\s*(?:ba)?sh|\b(?:npm|pnpm)\s+publish\b|\bkubectl\b|\bterraform\s+(?:apply|destroy)\b|\bchmod\s+777\b|\bDROP\s+(?:TABLE|DATABASE)\b)', re.I)


def evaluate(payload, *, cwd_is_execution_context=True):
    session_id = payload.get('session_id')
    if not session_id:
        return None  # No identity means no adoption or project discovery.
    try:
        binding = ownership.lookup(session_id)
    except (ValueError, OSError):
        return 'Veera session routing is invalid; do not access task state.'
    if binding is None:
        return None  # Critically: no cwd, ancestor, Git or run-state access.
    root = Path(binding['root'])
    cwd = Path(payload.get('cwd', '.')).resolve()
    if cwd_is_execution_context:
        if not cwd.is_relative_to(root):
            return 'This Veera session is bound to its task worktree; do not operate in another project.'
        # Nested repositories are separate projects even inside the owned path.
        for directory in [cwd, *cwd.parents]:
            if directory == root:
                break
            if (directory / '.git').exists():
                return 'Nested repository is not the owned Veera task.'
    try:
        capability = ownership.registry() / (ownership.session_key(session_id) + '.json')
        ownership.authorize(session_id, root, capability)
        run = status(root) if (root / STATE / 'state.json').exists() else {'status': 'preparing', 'contract': {'scope': []}}
    except Exception:
        return 'Owned Veera state is unavailable; no automatic adoption or repair.'
    tool = payload.get('tool_name', '')
    args = payload.get('tool_input', {})
    native_policy = os.environ.get('VEERA_HOST') in ('codex', 'dsh')
    if tool in ('Read', 'Glob', 'Grep'):
        target = args.get('file_path') or args.get('path') or str(cwd)
        path = (cwd / target).resolve()
        plugin = Path(__file__).resolve().parents[1]
        plugin_docs = (path.is_relative_to(plugin / 'docs') or path.is_relative_to(plugin / 'agents')
                       or path.is_relative_to(plugin / 'skills')
                       or path == plugin / 'adapters/codex/README.md'
                       or path.is_relative_to(plugin / 'adapters/codex/skills'))
        if not path.is_relative_to(root) and not plugin_docs:
            return 'Read/search target is outside this task; unrelated project context is not authorized.'
        if path.is_relative_to(root):
            for parent in [path if path.is_dir() else path.parent, *path.parents]:
                if parent == root:
                    break
                if (parent / '.git').exists():
                    return 'Nested project is outside the task read scope.'
        return None
    if tool == 'ListAgents':
        return 'Do not enumerate unrelated sessions; address only task agents by their recorded delegation IDs.'
    if tool == 'ToolSearch':
        return None
    if tool == 'Bash':
        raw_command = args.get('command', '')
        try:
            words = shell_words(raw_command)
        except ValueError:
            return 'Cannot validate malformed shell command.'
        lexer = shlex.shlex(raw_command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        compound = any(t in (';', '&&', '||', '|', '&', '>', '>>', '<') for t in lexer) or '$(' in raw_command or '`' in raw_command or '\n' in raw_command
        if compound and not native_policy:
            return 'ASK:Compound shell execution requires explicit confinement review'
        # Parse owner options in any order; never let duplicates hide approval rules.
        for flag, expected in (('--session-id', session_id), ('--capability-file', str(capability))):
            positions = [i for i, word in enumerate(words) if word == flag or word.startswith(flag + '=')]
            if len(positions) > 1:
                return 'Duplicate owner options are not allowed.'
            if positions:
                i = positions[0]
                if '=' in words[i]:
                    value = words[i].split('=', 1)[1]
                    del words[i]
                else:
                    if i + 1 >= len(words):
                        return 'Missing owner option value.'
                    value = words[i + 1]
                    del words[i:i + 2]
                if (Path(value).resolve() != Path(expected).resolve() if flag == '--capability-file' else value != expected):
                    return 'Controller identity does not match the calling host session.'
        # Required approval is recognized independently of other argument order.
        script_path = str(Path(__file__).resolve().parent / 'delivery.py')
        if not compound and controller_command(words):
            if words[2] in ('resume', 'amend', 'blocker-human-resolve'):
                if native_policy:
                    return None  # Controller validates identity, recorded user intent and state.
                return 'ASK:Explicit user approval is required for this authority-sensitive recovery operation'
        # Narrow escape hatch for reading/archiving finished state, never shell chains.
        script = str(Path(__file__).resolve().parent / 'delivery.py')
        if not compound and len(words) == 5 and controller_command(words) and words[2] in ('status', 'fingerprint', 'archive', 'context', 'unbind', 'dashboard-info') and words[3] == '--root' and Path(words[4]).resolve() == root:
            return None
        if not compound and len(words) == 7 and controller_command(words) and words[2] == 'blocker-human-resolve' and words[3] == '--root' and Path(words[4]).resolve() == root and words[5] == '--file':
            return 'ASK:Confirm the actual human-only blocker is resolved; agent advice cannot grant this authority'
        if not compound and len(words) == 7 and controller_command(words) and words[2] in ('checkpoint', 'resume') and words[3] == '--root' and Path(words[4]).resolve() == root:
            expected = '--file' if words[2] == 'resume' else '--reason'
            if words[5] == expected:
                # Ask the host/user rather than authorize a hard-budget extension ourselves.
                return 'ASK:Explicit approval required to resume stopped work' if words[2] == 'resume' else None
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        target = args.get('file_path') or args.get('notebook_path')
        if target:
            resolved = (cwd / target).resolve()
            if resolved.is_relative_to(root):
                for parent in [resolved.parent, *resolved.parents]:
                    if parent == root:
                        break
                    if (parent / '.git').exists():
                        return 'Write target belongs to a nested project, not this task.'
    if run['status'] in TERMINAL and tool in ('Write', 'Edit'):
        name = args.get('file_path', '')
        path = (cwd / name).resolve()
        if path.is_relative_to(root / '.veera-artifacts'):
            return None  # Preserve blocker/authorization evidence, never source changes.
    if run['status'] in TERMINAL:
        return 'Veera run is ' + run['status'] + '; no further mutating/execution tools in this run. Inspect state using read-only tools.'
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        name = args.get('file_path') or args.get('notebook_path')
        if not name:
            return 'Veera cannot establish the write target.'
        path = (cwd / name).resolve()
        if not path.is_relative_to(root):
            return 'Write target is outside the authorized repository.'
        relative = path.relative_to(root).as_posix()
        if any(part.lower() in ('.git', '.claude', '.codex', STATE) or part.lower().startswith('.env') or part.lower() in ('credentials.json', 'id_rsa', 'id_ed25519') for part in path.relative_to(root).parts):
            return 'Protected configuration, run state or secret file requires separate authorization.'
        if relative.startswith('.veera-artifacts/'):
            return None  # Evidence only; ignored source paths are never implementation scope.
        if not scoped(relative, run['contract']['scope']):
            return 'Write target is outside the frozen scope. PM must consult Architect/Advisor; do not silently expand scope.'
    if tool == 'Bash' and not native_policy:
        command = args.get('command', '')
        # Arbitrary shell can bypass path checks; require the host's approval,
        # rather than claiming this hook is a shell sandbox.
        try:
            tokens = shell_words(command)
        except ValueError:
            return 'Cannot validate malformed shell command.'
        script = str(Path(__file__).resolve().parent / 'delivery.py')
        if not controller_command(tokens):
            return 'ASK:Confirm this command is confined to the owned task and cannot affect another session/project'
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        if any(t in (';', '&&', '||', '|', '&', '>', '>>', '<') for t in lexer) or '$(' in command or '`' in command or '\n' in command:
            return 'ASK:Compound shell execution requires explicit confinement review'
        if DANGEROUS.search(command):
            return 'Destructive, publishing or infrastructure action is outside ordinary Build/Fix authorization.'
    if tool in ('Workflow', 'ScheduleWakeup', 'CronCreate'):
        return 'Veera does not authorize nested workflows or schedulers.'
    return None


def handle(payload, *, cwd_is_execution_context=True):
    # Classify only the exact host record before accessing any project state.
    try:
        if not isinstance(payload, dict):
            return {}
        key = ownership.session_key(payload.get('session_id'))
        path = ownership.registry() / (key + '.json')
        present = path.exists() or path.is_symlink()
    except (ValueError, OSError):
        return {}  # Unknown ownership cannot justify interfering with another session.
    if not present:
        from bootstrap import tool_context
        return tool_context(payload, os.environ.get('VEERA_HOST', 'claude'))
    try:
        reason = evaluate(payload, cwd_is_execution_context=cwd_is_execution_context)
    except Exception:
        reason = 'Owned Veera hook failed validation; controlled action denied.'
    if not reason:
        return {}
    decision = 'ask' if reason.startswith('ASK:') else 'deny'
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': decision, 'permissionDecisionReason': reason.removeprefix('ASK:')}}


def main():
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        print('{}')
        return
    print(json.dumps(handle(payload)))


if __name__ == '__main__':
    main()
