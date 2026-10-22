"""Owned worktrees and single-attempt, non-force publication for Veera."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

import delivery as d


def git(root, *args, timeout=30):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, timeout=timeout)
    d.require(result.returncode == 0, 'Git operation failed: ' + ' '.join(args[:2]) + '\n' + result.stderr[:2000])
    return result.stdout.strip()


def common(root):
    return Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir'))


@contextlib.contextmanager
def repository_lock(root):
    with (common(root) / 'veera-release.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def clean(root):
    # Exclude only reserved untracked task bookkeeping via per-command pathspecs.
    # Never edit shared ignore/configuration files to hide it from other sessions.
    tracked = git(root, 'ls-files', '--', '.veera', '.veera-artifacts')
    d.require(not tracked, 'Reserved task-state paths must not contain tracked source')
    output = git(root, 'status', '--porcelain', '--', '.', ':(exclude).veera', ':(exclude).veera-artifacts')
    d.require(not output, 'Checkout contains uncommitted changes; preserve them and resolve ownership first')


def workspace(root, task, session_id=None):
    root = Path(root).resolve()
    d.require(re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}', task), 'Task must be a short lowercase slug')
    d.require(Path(git(root, 'rev-parse', '--show-toplevel')).resolve() == root, 'Use repository root')
    with repository_lock(root):
        clean(root)
        base = git(root, 'rev-parse', 'refs/heads/main')
        d.require(git(root, 'rev-parse', 'HEAD') == base, 'Start from main or a branch at exactly main; unrelated topic commits must not enter the task')
        branch = 'veera/' + task
        target = root.parent / (root.name + '-veera-' + task)
        d.require(not target.exists(), 'Worktree destination already exists')
        git(root, 'worktree', 'add', '-b', branch, str(target), base)
        metadata = {'id': uuid.uuid4().hex, 'root': str(target), 'original': str(root), 'branch': branch, 'base': base, 'common': str(common(root)), 'created_at': time.time()}
        metadata['session_id'] = session_id
        d.atomic(d.storage(target) / 'workspace.json', metadata)
        if session_id is not None:
            import ownership
            metadata['capability_file'] = ownership.enroll(session_id, target, metadata['id'])
        return metadata


def owned(root):
    root = Path(root).resolve()
    meta = d.read_json(d.storage(root) / 'workspace.json')
    d.require(meta['root'] == str(root) and meta['common'] == str(common(root)), 'Workspace ownership does not match this checkout')
    d.require((root / '.git').is_file(), 'Task must use a linked worktree')
    d.require(git(root, 'branch', '--show-current') == meta['branch'], 'Task branch changed')
    d.require(meta['branch'].startswith('veera/'), 'Not an owned task branch')
    return meta


def validate_inputs(root, scope):
    ignored = git(root, 'ls-files', '--others', '--ignored', '--exclude-standard', '--', *scope)
    d.require(not ignored, 'Ignored untracked application inputs in scope are not releasable; track them explicitly before the task: ' + ignored[:500])


def release_policy(state):
    policy = state['contract'].get('release', {})
    d.require(policy.get('branch') == 'main' and policy.get('push_authorized') is True, 'Release needs explicit main/remote push authorization')
    d.require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', policy.get('remote', '')), 'Use a configured remote name')
    name = policy.get('version_file', '')
    d.require(isinstance(name, str) and name and not Path(name).is_absolute() and '..' not in Path(name).parts, 'Version file must be repository-relative')
    d.require(d.scoped(name, state['contract']['scope']), 'Version file must be included in scope upfront')
    return policy


def version_value(path):
    text = path.read_text()
    value = json.loads(text)['version'] if path.suffix == '.json' else text.strip()
    match = re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value)
    d.require(match is not None, 'Only plain x.y.z patch versions supported; complex release schemes need a project adapter')
    return value, '.'.join([match[1], match[2], str(int(match[3]) + 1)])


def commit_scope(root, state, message):
    validate_inputs(root, state['contract']['scope'])
    paths = d.changed(state, d.snapshot(root))
    d.require(all(d.scoped(p, state['contract']['scope']) for p in paths), 'Out-of-scope source changes')
    if paths:
        git(root, 'add', '-A', '--', *paths)
    if git(root, 'diff', '--cached', '--name-only'):
        git(root, 'commit', '-m', message + '\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')
    clean(root)


def prepare(root):
    """Integrate latest main in isolation; version is the last planned source edit."""
    root = Path(root).resolve()
    with repository_lock(root), d.locked(root) as directory:
        state = d.load(directory)
        d.expire(state)
        d.save(directory, state)
        d.active(state)
        owned(root)
        policy = release_policy(state)
        d.require(not state.get('running'), 'Check still running')
        d.require(state['phase'] == 'implement', 'Prepare release after implementation, before final verification')
        if state.get('release_prepared'):
            return state  # Do not increment version or repeat integration implicitly.
        remote = policy['remote']
        git(root, 'fetch', '--no-tags', remote, 'refs/heads/main')
        remote_tip = git(root, 'rev-parse', 'FETCH_HEAD')
        local_tip = git(root, 'rev-parse', 'refs/heads/main')
        # Include all existing main work; diverged main requires an explicit resolution.
        ancestors = subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', local_tip, remote_tip]).returncode
        target = remote_tip if ancestors == 0 else local_tip
        d.require(ancestors == 0 or subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', remote_tip, local_tip]).returncode == 0, 'Local and remote main diverged; do not overwrite either')
        commit_scope(root, state, 'Veera: checkpoint task before main integration')
        # Merge only main into the owned task, never merge unrelated branches.
        try:
            git(root, 'merge', '--no-edit', target)
        except d.DeliveryError:
            state['status'] = 'blocked'
            d.event(state, 'integration-blocked', 'Resolve conflicts in task worktree; main untouched')
            d.save(directory, state)
            raise
        # Main changes are incorporated baseline, not task scope drift.
        base_files = d.snapshot(root)
        for name in set(state['baseline']) | set(base_files):
            if not d.scoped(name, state['contract']['scope']):
                if name in base_files:
                    state['baseline'][name] = base_files[name]
                else:
                    state['baseline'].pop(name, None)
        path = (root / policy['version_file']).resolve()
        d.require(path.is_relative_to(root) and path.is_file() and not (root / policy['version_file']).is_symlink(), 'Version target missing or unsafe')
        old, new = version_value(path)
        main_text = git(root, 'show', target + ':' + policy['version_file'])
        main_version = json.loads(main_text)['version'] if path.suffix == '.json' else main_text.strip()
        d.require(old == main_version, 'Task must not modify the release version; patch increment is based on integrated main')
        if path.suffix == '.json':
            data = json.loads(path.read_text())
            data['version'] = new
            path.write_text(json.dumps(data, indent=2) + '\n')
        else:
            path.write_text(new + '\n')
        state['release_prepared'] = {'remote_tip': remote_tip, 'local_tip': local_tip, 'integrated_tip': target, 'version_from': old, 'version_to': new, 'version_file': policy['version_file']}
        state['checks'] = {}
        state['review'] = None
        d.event(state, 'release-prepared', state['release_prepared'])
        d.save(directory, state)
        return state


def reconcile(root, reason):
    """Reintegrate changed main within the same repair/time budget, before any push."""
    with repository_lock(root), d.locked(root) as directory:
        state = d.load(directory)
        d.active(state)
        d.require(not state.get('push_attempted'), 'Cannot retry/reconcile automatically after a push attempt')
        d.require(state.get('release_prepared') and reason.strip(), 'Reconciliation needs a prepared release and new evidence')
        d.require(not state.get('running'), 'Check still running')
        d.require(state['repairs'] < state['contract'].get('max_repairs', 3), 'Repair ceiling exhausted')
        plan = state['release_prepared']
        path = Path(root) / plan['version_file']
        d.require(version_value(path)[0] == plan['version_to'], 'Version differs from prepared value; inspect before reconciliation')
        if path.suffix == '.json':
            data = json.loads(path.read_text())
            data['version'] = plan['version_from']
            path.write_text(json.dumps(data, indent=2) + '\n')
        else:
            path.write_text(plan['version_from'] + '\n')
        state['repairs'] += 1
        state['phase'] = 'implement'
        state['status'] = 'active'
        state['release_prepared'] = None
        state['checks'] = {}
        state['review'] = None
        d.event(state, 'reconcile', reason)
        d.save(directory, state)
    return prepare(root)


def main_worktree(root):
    records = git(root, 'worktree', 'list', '--porcelain').split('\n\n')
    for record in records:
        lines = record.splitlines()
        if 'branch refs/heads/main' in lines:
            return Path(next(line[9:] for line in lines if line.startswith('worktree ')))
    return None


def validate_evidence(root, state):
    from task_context import require_clear
    require_clear(state)
    fingerprint = d.digest(d.snapshot(root))
    d.require(state.get('review') and state['review']['fingerprint'] == fingerprint, 'Release review is stale')
    for spec in state['contract']['checks']:
        result = state['checks'].get(spec['id'], {})
        d.require(result.get('status') == 'passed' and result.get('fingerprint') == fingerprint, 'Missing or stale required release check')
        for name, sha in result.get('artifacts', {}).items():
            path = (root / name).resolve()
            d.require(path.is_relative_to(root) and path.is_file() and d.hashlib.sha256(path.read_bytes()).hexdigest() == sha, 'Visual evidence changed after review')
    return fingerprint


def publish(root):
    root = Path(root).resolve()
    with repository_lock(root), d.locked(root) as directory:
        state = d.load(directory)
        d.expire(state)
        d.save(directory, state)
        d.active(state)
        owned(root)
        policy = release_policy(state)
        d.require(state['status'] == 'ready' and state.get('release_prepared'), 'Publish requires final verified ready state')
        d.require(not state.get('push_attempted'), 'Push already attempted; reconcile outcome, never automatically retry')
        d.require(main_worktree(root) is None, 'Main is checked out in another worktree; do not inspect or modify that session. Publication blocked before push.')
        fingerprint = validate_evidence(root, state)
        plan = state['release_prepared']
        d.require(version_value(root / plan['version_file'])[0] == plan['version_to'], 'Version changed after prepare')
        remote = policy['remote']
        # Fetch/reconcile may run multiple times; publication itself is at most once.
        git(root, 'fetch', '--no-tags', remote, 'refs/heads/main')
        d.require(git(root, 'rev-parse', 'FETCH_HEAD') == plan['remote_tip'], 'Remote main advanced; reintegrate and fully reverify before publication')
        d.require(git(root, 'rev-parse', 'refs/heads/main') == plan['local_tip'], 'Local main advanced; reintegrate and fully reverify')
        commit_scope(root, state, 'Veera: verified delivery ' + plan['version_to'])
        d.require(d.digest(d.snapshot(root)) == fingerprint, 'Commit hooks changed the verified source; reverify')
        tip = git(root, 'rev-parse', 'HEAD')
        validate_evidence(root, state)
        d.require(subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', plan['local_tip'], tip]).returncode == 0, 'Task is not a fast-forward of main')
        # The only allowed push. Persist intent before invoking Git to survive ambiguity.
        state['push_attempted'] = {'tip': tip, 'remote': remote, 'at': time.time(), 'result': 'unknown'}
        d.event(state, 'push-start', state['push_attempted'])
        d.save(directory, state)
        try:
            git(root, 'push', '--porcelain', remote, tip + ':refs/heads/main', timeout=60)
            observed = git(root, 'ls-remote', remote, 'refs/heads/main').split()[0]
            d.require(observed == tip, 'Publication cannot be confirmed; reconcile without another push')
            state['push_attempted']['result'] = 'confirmed'
            # Remote delivery does not grant ownership of any local checkout/ref.
            state['status'] = 'complete'
            d.event(state, 'complete', 'Full verified task and one confirmed remote main push; local main and peer checkouts untouched')
        except (d.DeliveryError, subprocess.SubprocessError, OSError) as error:
            state['status'] = 'blocked'
            d.event(state, 'publication-blocked', str(error))
            d.save(directory, state)
            raise
        d.save(directory, state)
        return state
