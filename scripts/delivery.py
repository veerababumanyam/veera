#!/usr/bin/env python3
"""Local, dependency-free delivery state machine. Not a sandbox."""
import argparse
import contextlib
from platform_runtime import file_lock, launch
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import selectors
import uuid

STATE = '.veera'
TERMINAL = {'complete', 'blocked', 'budget-exhausted', 'user-stopped'}
PHASES = ['discover', 'plan', 'implement', 'verify', 'review']


class DeliveryError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise DeliveryError(message)


def read_json(path):
    return json.loads(Path(path).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def storage(root):
    root = Path(root).resolve()
    directory = root / STATE
    require(not directory.is_symlink(), 'State directory must not be a symlink')
    directory.mkdir(mode=0o700, exist_ok=True)
    for item in directory.iterdir():
        require(not item.is_symlink(), 'State artifacts must not be symlinks')
    return directory


def atomic(path, value):
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def locked(root):
    directory = storage(root)
    with file_lock(directory / 'lock'):
        yield directory


def event(state, kind, detail):
    state['events'].append({'at': time.time(), 'kind': kind, 'detail': detail})
    state['updated_at'] = time.time()


def save(directory, state):
    atomic(directory / 'state.json', state)


def load(directory):
    state = read_json(directory / 'state.json')
    require(digest(state['contract']) == state['contract_hash'], 'Contract integrity mismatch')
    return state


def expire(state):
    if state['status'] not in TERMINAL and state.get('soft_deadline') and time.time() >= state['soft_deadline'] and not state.get('soft_notified'):
        state['soft_notified'] = True
        state['replan_required'] = True
        event(state, 'replan', 'Soft target reached: PM/Architect/Advisor must replan and continue the full task; do not abandon or weaken acceptance')
    if state['status'] not in TERMINAL and time.time() >= state['deadline']:
        state['status'] = 'budget-exhausted'
        event(state, 'stop', 'Absolute wall-clock budget exhausted; no automatic renewal')


def active(state):
    expire(state)
    require(state['status'] not in TERMINAL, 'Run is ' + state['status'])


def snapshot(root, scope=None):
    root = Path(root).resolve()
    if scope is None and (root / STATE / 'state.json').is_file():
        scope = read_json(root / STATE / 'state.json')['contract']['scope']
    result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], capture_output=True, check=True, timeout=15)
    names = set(os.fsdecode(result.stdout).split('\0'))
    if scope:
        ignored = subprocess.run(['git', '-C', str(root), 'ls-files', '-z', '--others', '--ignored', '--exclude-standard', '--', *scope], capture_output=True, check=True, timeout=15)
        names.update(os.fsdecode(ignored.stdout).split('\0'))
    files = {}
    for name in sorted(names - {''}):
        if name == STATE or name.startswith(STATE + '/') or name == '.veera-artifacts' or name.startswith('.veera-artifacts/'):
            tracked = subprocess.run(['git', '-C', str(root), 'ls-files', '--error-unmatch', '--', name], capture_output=True, timeout=10)
            require(tracked.returncode != 0, 'Reserved state/evidence path contains tracked source: ' + name)
            continue
        path = root / name
        if path.is_symlink():
            files[name] = digest({'symlink': os.readlink(path)})
        elif path.is_file():
            require(path.stat().st_size <= 32 * 1024 * 1024, 'File too large to fingerprint: ' + name)
            files[name] = hashlib.sha256(path.read_bytes() + str(path.stat().st_mode & 0o777).encode()).hexdigest()
        elif not path.exists():
            files[name] = 'deleted'
        else:
            raise DeliveryError('Unsupported repository entry (such as a submodule): ' + name)
    return files


def scoped(name, scope):
    return any(name == entry.rstrip('/') or name.startswith(entry.rstrip('/') + '/') for entry in scope)


def changed(state, current):
    base = state['baseline']
    return sorted(name for name in set(base) | set(current) if base.get(name) != current.get(name))


def validate_contract(contract, root):
    require(isinstance(contract, dict), 'Contract must be an object')
    for key in ('scope', 'criteria', 'checks'):
        require(isinstance(contract.get(key), list) and contract[key], key + ' must be a nonempty list')
    for name in contract['scope']:
        require(isinstance(name, str) and name and not Path(name).is_absolute() and '..' not in Path(name).parts and name not in ('.', './'), 'Use explicit repository-relative scope')
        require(not any(p in ('.git', STATE, '.claude', '.veera-artifacts') for p in Path(name).parts), 'Protected scope entry')
        require((root / name).resolve().is_relative_to(root), 'Scope escapes repository')
    checks = set()
    for check in contract['checks']:
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,64}', check.get('id', '')) and check['id'] not in checks, 'Invalid or duplicate check ID')
        checks.add(check['id'])
        require(isinstance(check.get('argv'), list) and check['argv'] and all(isinstance(x, str) and x for x in check['argv']), 'Check needs argv strings, not a shell expression')
        require(check.get('kind') in ('test', 'static', 'visual'), 'Unknown check kind')
        timeout = check.get('timeout_seconds', 120)
        require(isinstance(timeout, (float, int)) and math.isfinite(timeout) and 0 < timeout <= 3600, 'Invalid check timeout')
        if check['kind'] == 'test':
            pattern = re.compile(check.get('count_pattern', ''))
            require(pattern.groups == 1, 'Tests require count_pattern with one capture group')
        if check['kind'] == 'visual':
            require(check.get('artifacts') and all(isinstance(p, str) and not Path(p).is_absolute() and '..' not in Path(p).parts for p in check['artifacts']), 'Visual checks require relative artifact paths')
    ids = set()
    for criterion in contract['criteria']:
        require(isinstance(criterion.get('id'), str) and criterion['id'] and criterion['id'] not in ids, 'Invalid or duplicate criterion ID')
        ids.add(criterion['id'])
        require(criterion.get('text') and criterion.get('checks') and set(criterion['checks']) <= checks, 'Each criterion needs text and known checks')
    require(isinstance(contract.get('max_repairs', 3), int) and 0 <= contract.get('max_repairs', 3) <= 3, 'Repair ceiling must be 0–3')
    if contract.get('ui'):
        require(contract.get('visual_references'), 'UI work requires visual references')
        for reference in contract['visual_references']:
            path = (root / reference).resolve()
            require(path.is_relative_to(root) and path.is_file(), 'Visual reference missing or outside repository')
        require(any(c['kind'] == 'visual' for c in contract['checks']), 'UI work requires a visual check')


def init(root, mode, request, contract, minutes, hard_minutes=None):
    root = Path(root).resolve()
    require(math.isfinite(minutes) and 0 < minutes <= 240, 'Budget must be >0 and <=240 minutes')
    require(request.strip(), 'Request must not be empty')
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], text=True, timeout=10).strip()
    require(Path(actual).resolve() == root, 'Use the repository root')
    validate_contract(contract, root)
    if hard_minutes is not None:
        require(math.isfinite(hard_minutes) and minutes <= hard_minutes <= 480, 'Hard ceiling must cover soft target and be <=480 minutes')
        from git_delivery import owned, release_policy, validate_inputs, git, clean
        metadata = owned(root)
        require(git(root, 'rev-parse', 'HEAD') == metadata['base'], 'Worktree HEAD changed before init; do not absorb unapproved commits into baseline')
        clean(root)
        release_policy({'contract': contract})
        validate_inputs(root, contract['scope'])
    with locked(root) as directory:
        require(not (directory / 'state.json').exists(), 'Run already exists; budget cannot be reset by init')
        now = time.time()
        state = {'version': 1, 'run_id': uuid.uuid4().hex, 'root': str(root), 'mode': mode, 'request': request, 'status': 'active', 'phase': 'discover', 'started_at': now, 'updated_at': now, 'deadline': now + minutes * 60, 'contract': contract, 'contract_hash': digest(contract), 'baseline': snapshot(root, contract['scope']), 'checks': {}, 'review': None, 'repairs': 0, 'events': [], 'usage': {'cost_usd': None, 'cache_read_tokens': None, 'cache_creation_tokens': None}}
        if hard_minutes is not None:
            state['version'] = 2
            state['soft_deadline'] = now + minutes * 60
            state['deadline'] = now + hard_minutes * 60
            state['replan_required'] = False
        event(state, 'init', 'Acceptance contract frozen; PM owns allocation within the fixed ceiling')
        save(directory, state)
        return state


def status(root):
    with locked(root) as directory:
        state = load(directory)
        expire(state)
        save(directory, state)
        return state


def mutate(root, operation):
    with locked(root) as directory:
        state = load(directory)
        expire(state)
        save(directory, state)
        active(state)
        result = operation(state)
        save(directory, state)
        return result or state


def phase(root, name):
    def update(state):
        require(name in PHASES, 'Unknown phase')
        current = PHASES.index(state['phase'])
        require(PHASES.index(name) in (current, current + 1), 'Use ordered phases; repair explicitly to go back')
        require(not state.get('running'), 'A check is still running')
        state['phase'] = name
        event(state, 'phase', name)
    return mutate(root, update)


def repair(root, reason):
    def update(state):
        require(reason.strip(), 'Repair needs new evidence or a changed hypothesis')
        require(state['phase'] in ('verify', 'review'), 'Repair follows verification/review')
        require(not state.get('running'), 'A check is still running')
        if state['repairs'] >= state['contract'].get('max_repairs', 3):
            if state.get('version', 1) >= 2:
                state['repair_escalation'] = True
                event(state, 'escalation', 'Repair ceiling reached: record blocker and consult Advisor/Architect/PM; no reset or extra retry')
            else:
                state['status'] = 'blocked'
                event(state, 'stop', 'Repair ceiling reached')
            return
        require(reason not in [e['detail'] for e in state['events'] if e['kind'] == 'repair'], 'Unchanged repair attempt refused')
        state['repairs'] += 1
        state['phase'] = 'implement'
        state['review'] = None
        event(state, 'repair', reason)
    return mutate(root, update)


def kill_group(process):
    if os.name == 'nt':
        # The launcher owns a kill-on-close job containing all descendants.
        if process.poll() is None:
            process.kill()
        process.wait()
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def check(root, check_id):
    root = Path(root).resolve()
    with locked(root) as directory:
        state = load(directory)
        expire(state)
        save(directory, state)
        active(state)
        require(state['phase'] == 'verify', 'Checks run during verify phase')
        require(not state.get('running'), 'Another check is running; inspect before recovery')
        spec = next((c for c in state['contract']['checks'] if c['id'] == check_id), None)
        require(spec is not None, 'Unknown check ID')
        before = snapshot(root)
        previous = state['checks'].get(check_id)
        require(not (previous and previous['status'] == 'failed' and previous.get('repair_attempt') == state['repairs']), 'Failed check requires an explicit bounded repair before rerun')
        require(all(scoped(p, state['contract']['scope']) for p in changed(state, before)), 'Out-of-scope changes detected')
        state['running'] = check_id
        event(state, 'check-start', check_id)
        save(directory, state)
        deadline = min(state['deadline'], time.time() + spec.get('timeout_seconds', 120))
    log = directory / (check_id + '-' + uuid.uuid4().hex + '.log')
    code, why, process = None, '', None
    limit = 8 * 1024 * 1024
    started = time.time()
    try:
        with log.open('wb') as output:
            process = launch(spec['argv'], root)
            os.set_blocking(process.stdout.fileno(), False)
            size, eof, exited_at = 0, False, None
            with (contextlib.nullcontext() if os.name == 'nt' else selectors.DefaultSelector()) as selector:
                if selector is not None:
                    selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    now = time.time()
                    if now >= deadline:
                        why = 'timeout'
                        break
                    if status(root)['status'] in TERMINAL:
                        why = 'run-stopped'
                        break
                    if process.poll() is not None:
                        exited_at = exited_at or now
                        if eof:
                            break
                        if now - exited_at >= .5:
                            why = 'output-capture-incomplete'
                            break
                    if selector is None:
                        # Windows selectors only accept sockets, not pipe handles.
                        time.sleep(.005)
                        ready = [] if eof else [(None, None)]
                    else:
                        ready = selector.select(timeout=.05)
                    for key, _ in ready:
                        try:
                            chunk = os.read(process.stdout.fileno(), 65536)
                        except BlockingIOError:
                            continue
                        if not chunk:
                            eof = True
                            if selector is not None:
                                selector.unregister(process.stdout)
                            continue
                        output.write(chunk[:max(0, limit - size)])
                        size += len(chunk)
                        if size > limit:
                            why = 'output-limit'
                            break
                    if why:
                        break
            # Raw nonblocking pipe has no competing reader lock during cleanup.
            kill_group(process)
            code = process.wait()
            process.stdout.close()
    except (OSError, KeyboardInterrupt) as error:
        why = type(error).__name__
        if process is not None:
            kill_group(process)
    with locked(root) as directory:
        state = load(directory)
        after = snapshot(root)
        with log.open('rb') as stream:
            text = stream.read(limit).decode(errors='replace')
        count = None
        if spec['kind'] == 'test':
            matches = re.findall(spec['count_pattern'], text)
            try:
                count = sum(int(x) for x in matches)
            except ValueError:
                count = 0
        artifacts = {}
        if spec['kind'] == 'visual':
            for name in spec['artifacts']:
                path = (root / name).resolve()
                if path.is_relative_to(root) and path.is_file() and path.stat().st_size and path.stat().st_mtime >= started:
                    artifacts[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        passed = code == 0 and not why and before == after and (spec['kind'] != 'test' or bool(count and count > 0)) and (spec['kind'] != 'visual' or len(artifacts) == len(spec['artifacts']))
        result = {'id': check_id, 'repair_attempt': state['repairs'], 'status': 'passed' if passed else 'failed', 'argv': spec['argv'], 'exit_code': code, 'test_count': count, 'fingerprint': digest(before), 'elapsed_seconds': time.time() - started, 'reason': why or ('repository changed during check' if before != after else ''), 'log': log.name, 'artifacts': artifacts}
        state['checks'][check_id] = result
        state['running'] = None
        expire(state)
        event(state, 'check-end', result)
        save(directory, state)
        return result


def review(root, report):
    def update(state):
        require(state['phase'] == 'review', 'Review follows verify')
        require(not state.get('running'), 'Check still running')
        require(report.get('reviewer') and report.get('notes'), 'Independent reviewer identity and rationale required')
        require(report.get('approved') is True, 'Review has unresolved findings')
        require(set(report.get('criteria', [])) == {c['id'] for c in state['contract']['criteria']}, 'Review must cover all criteria')
        require(report.get('fingerprint') == digest(snapshot(root)), 'Review does not match current code')
        state['review'] = report
        event(state, 'review', report)
    return mutate(root, update)


def finish(root):
    def update(state):
        from task_context import require_clear
        require_clear(state)
        require(state['phase'] == 'review' and not state.get('running'), 'Finish requires completed review')
        current = snapshot(root)
        require(all(scoped(p, state['contract']['scope']) for p in changed(state, current)), 'Out-of-scope changes detected')
        fingerprint = digest(current)
        for spec in state['contract']['checks']:
            result = state['checks'].get(spec['id'], {})
            require(result.get('status') == 'passed' and result.get('fingerprint') == fingerprint, 'Missing, failed or stale check: ' + spec['id'])
            for name, sha in result.get('artifacts', {}).items():
                path = (Path(root) / name).resolve()
                require(path.is_relative_to(Path(root).resolve()) and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == sha, 'Visual evidence changed')
        require(state.get('review') and state['review']['fingerprint'] == fingerprint, 'Missing or stale independent review')
        if state.get('version', 1) >= 2:
            require(state.get('release_prepared'), 'Release integration/version bump must precede final verification')
            require(not state.get('replan_required'), 'Record PM/Architect/Advisor replan before claiming readiness')
            state['status'] = 'ready'
            event(state, 'ready', 'Implementation verified; publication still required, NOT DONE')
        else:
            state['status'] = 'complete'
            event(state, 'complete', 'Legacy v1 verification complete; publication not claimed')
    return mutate(root, update)


def stop(root, reason, expected_run_id=None):
    with locked(root) as directory:
        state = load(directory)
        require(expected_run_id is None or expected_run_id == state['run_id'], 'Dashboard belongs to a different run')
        require(reason.strip(), 'Stop reason required')
        if state['status'] not in TERMINAL:
            state['status'] = 'user-stopped'
            event(state, 'stop', reason)
            save(directory, state)
        return state


def archive(root):
    """Archive only completed runs; never renew incomplete work through this API."""
    with locked(root) as directory:
        state = load(directory)
        require(state['status'] == 'complete', 'Only verified completed runs can be archived automatically; unresolved runs require explicit human disposition')
        require(not state.get('running'), 'A check is still running')
        history = directory / 'history'
        require(not history.is_symlink(), 'Archive directory must not be a symlink')
        history.mkdir(mode=0o700, exist_ok=True)
        target = history / str(time.time_ns())
        target.mkdir(mode=0o700)
        for path in directory.iterdir():
            if path.is_file() and path.name != 'lock':
                os.replace(path, target / path.name)
        return {'status': 'archived', 'path': str(target)}


def checkpoint(root, note):
    with locked(root) as directory:
        state = load(directory)
        require(not state.get('running'), 'Do not checkpoint an ambiguous running check')
        state['checkpoint'] = {'id': uuid.uuid4().hex, 'at': time.time(), 'fingerprint': digest(snapshot(root)), 'note': note, 'phase': state['phase']}
        event(state, 'checkpoint', state['checkpoint'])
        save(directory, state)
        return state


def resume(root, report):
    with locked(root) as directory:
        state = load(directory)
        require(state.get('version', 1) >= 2 and state['status'] in ('blocked', 'budget-exhausted', 'user-stopped'), 'Only stopped v2 work may resume')
        require(not state.get('push_attempted') and not state.get('running'), 'Reconcile publication/running command manually before resume')
        saved = state.get('checkpoint', {})
        require(saved and saved['id'] == report.get('checkpoint_id'), 'Use the exact saved checkpoint')
        require(saved['fingerprint'] == digest(snapshot(root)), 'Checkpoint source changed; inspect and record a new checkpoint')
        require(report.get('authorization') and report.get('reason'), 'Resume requires actual user authorization and resolved blocker evidence')
        extra = report.get('additional_minutes', 0)
        require(isinstance(extra, (int, float)) and math.isfinite(extra) and 0 <= extra <= 120, 'Invalid explicit time allowance')
        if extra:
            state['deadline'] = max(time.time(), state['deadline']) + extra * 60
        require(state['deadline'] > time.time(), 'Hard budget exhausted; new user-authorized allowance is necessary')
        require(state['repairs'] < state['contract'].get('max_repairs', 3), 'Repair ceiling remains exhausted; resume cannot reset it')
        state['status'] = 'active'
        state['checks'] = {}
        state['review'] = None
        state['phase'] = 'implement'
        state['replan_required'] = True
        event(state, 'resume', report)
        save(directory, state)
        return state


def decision(root, report):
    def update(state):
        require(report.get('owner') == 'pm' and {'architect', 'advisor'} <= set(report.get('consulted', [])), 'Material decisions require PM ownership and Architect/Advisor consultation')
        require(report.get('decision') and report.get('reason'), 'Decision and rationale required')
        if state.get('repair_escalation'):
            from task_context import sources
            evidence = sources(root, report.get('evidence'))
            state['repair_escalation_decision'] = {'decision': report['decision'], 'evidence': evidence}
        state['replan_required'] = False
        event(state, 'decision', report)
    return mutate(root, update)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for command in ('init', 'status', 'phase', 'check', 'review', 'finish', 'stop', 'repair', 'decision', 'dashboard', 'fingerprint', 'archive', 'workspace', 'release-prepare', 'publish', 'checkpoint', 'resume', 'release-reconcile', 'context', 'context-import', 'context-item', 'blocker', 'blocker-human-resolve', 'unbind'):
        sub = subs.add_parser(command)
        sub.add_argument('--root', required=True, type=Path)
        sub.add_argument('--session-id', required=True)
        if command != 'workspace':
            sub.add_argument('--capability-file', required=True)
        if command == 'init':
            sub.add_argument('--mode', choices=['build', 'fix'], required=True)
            sub.add_argument('--request', required=True)
            sub.add_argument('--contract', required=True)
            sub.add_argument('--minutes', type=float, default=30)
            sub.add_argument('--hard-minutes', type=float, default=120)
        elif command == 'workspace':
            sub.add_argument('--task', required=True)
        elif command == 'phase':
            sub.add_argument('--name', choices=PHASES, required=True)
        elif command in ('check', 'context-item'):
            sub.add_argument('--id', required=True)
        elif command in ('review', 'decision', 'resume', 'context-import', 'blocker', 'blocker-human-resolve'):
            sub.add_argument('--file', required=True)
        elif command in ('stop', 'repair', 'checkpoint', 'release-reconcile'):
            sub.add_argument('--reason', required=True)
        elif command == 'dashboard':
            sub.add_argument('--port', type=int, default=0)
    subs.add_parser('doctor')
    args = parser.parse_args()
    try:
        command = args.command
        if command != 'doctor':
            import ownership
            if command == 'workspace':
                require(ownership.lookup(args.session_id) is None, 'Session already bound; do not overwrite its task')
            else:
                ownership.authorize(args.session_id, args.root, args.capability_file)
        if command == 'doctor':
            result = {'python': sys.version.split()[0], 'git': subprocess.check_output(['git', '--version'], text=True).strip(), 'platform': sys.platform, 'status': 'available', 'sandbox': False}
        elif command == 'unbind':
            result = ownership.unbind(args.session_id, args.root, args.capability_file)
        elif command == 'init':
            result = init(args.root, args.mode, args.request, read_json(args.contract), args.minutes, args.hard_minutes)
        elif command in ('workspace', 'release-prepare', 'publish'):
            import git_delivery
            if command == 'workspace':
                result = git_delivery.workspace(args.root, args.task, args.session_id)
            elif command == 'release-prepare':
                result = git_delivery.prepare(args.root)
            else:
                result = git_delivery.publish(args.root)
        elif command == 'phase':
            result = phase(args.root, args.name)
        elif command == 'check':
            result = check(args.root, args.id)
        elif command in ('context', 'context-item', 'context-import', 'blocker', 'blocker-human-resolve'):
            import task_context
            if command == 'context':
                result = task_context.context(args.root)
            elif command == 'context-item':
                result = task_context.item(args.root, args.id)
            elif command == 'context-import':
                result = task_context.import_context(args.root, read_json(args.file))
            elif command == 'blocker-human-resolve':
                result = task_context.human_resolve(args.root, read_json(args.file))
            else:
                result = task_context.blocker(args.root, read_json(args.file))
        elif command in ('review', 'decision', 'resume'):
            result = globals()[command](args.root, read_json(args.file))
        elif command == 'release-reconcile':
            from git_delivery import reconcile
            result = reconcile(args.root, args.reason)
        elif command in ('stop', 'repair', 'checkpoint'):
            result = globals()[command](args.root, args.reason)
        elif command == 'fingerprint':
            result = {'fingerprint': digest(snapshot(args.root))}
        elif command == 'dashboard':
            from dashboard import serve
            serve(args.root, args.port)
            return
        else:
            result = globals()[command](args.root)
        print(json.dumps(result, indent=2))
        if result.get('status') in ('failed', 'blocked', 'budget-exhausted'):
            sys.exit(1)
    except (DeliveryError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
