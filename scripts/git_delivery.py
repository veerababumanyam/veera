"""Owned worktrees and single-attempt, non-force publication for Veera."""
import contextlib
import copy
from platform_runtime import file_lock
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
    with file_lock(common(root) / 'veera-release.lock', blocking=False):
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
    if session_id is not None:
        import ownership
        d.require(ownership.lookup(session_id) is None, 'Session already bound; do not adopt or overwrite a task')
    d.require(Path(git(root, 'rev-parse', '--show-toplevel')).resolve() == root, 'Use repository root')
    with repository_lock(root):
        branch = 'veera/' + task
        target = root.parent / (root.name + '-veera-' + task)
        if target.exists() or target.is_symlink() or (hasattr(target, 'is_junction') and target.is_junction()):
            return recover_workspace(root, target, branch, session_id)
        clean(root)
        base = git(root, 'rev-parse', 'refs/heads/main')
        d.require(git(root, 'rev-parse', 'HEAD') == base, 'Start from main or a branch at exactly main; unrelated topic commits must not enter the task')
        git(root, 'worktree', 'add', '-b', branch, str(target), base)
        metadata = {'id': uuid.uuid4().hex, 'root': str(target), 'original': str(root), 'branch': branch, 'base': base, 'common': str(common(root)), 'created_at': time.time()}
        metadata['session_id'] = session_id
        d.atomic(d.storage(target) / 'workspace.json', metadata)
        if session_id is not None:
            import ownership
            metadata['capability_file'] = ownership.enroll(session_id, target, metadata['id'])
        return metadata


def recover_workspace(root, target, branch, session_id):
    """Finish enrollment of this owner's unchanged pre-init workspace only.

    Called under the original repository lock. Metadata is never rewritten and
    current main is not a replacement for the recorded creation baseline.
    """
    import ownership
    d.require(session_id is not None, 'Partial workspace recovery requires its original session owner')
    paths = (target, target / '.git', target / d.STATE, target / d.STATE / 'workspace.json')
    d.require(not any(p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()) for p in paths), 'Partial workspace paths must not be symlinks or junctions')
    metadata_path = target / d.STATE / 'workspace.json'
    d.require(metadata_path.is_file(), 'Existing destination has no recoverable workspace metadata')
    metadata = d.read_json(metadata_path)
    d.require(isinstance(metadata, dict) and metadata.get('session_id') == session_id, 'Partial workspace belongs to a different session')
    d.require(metadata.get('root') == str(target) and metadata.get('original') == str(root) and metadata.get('branch') == branch, 'Partial workspace identity differs from requested original/task')
    d.require(isinstance(metadata.get('id'), str) and re.fullmatch(r'[0-9a-f]{32}', metadata['id']), 'Invalid partial workspace identity')
    d.require(isinstance(metadata.get('base'), str) and re.fullmatch(r'[0-9a-f]{40,64}', metadata['base']), 'Invalid recorded workspace base')
    state_path = target / d.STATE / 'state.json'
    d.require(not state_path.exists() and not state_path.is_symlink(), 'Initialized tasks cannot use partial workspace recovery')
    d.require((target / '.git').is_file(), 'Recovery requires the original linked worktree')
    shared = common(root)
    d.require(metadata.get('common') == str(shared) and common(target) == shared, 'Partial workspace Git repository differs')
    d.require(Path(git(target, 'rev-parse', '--show-toplevel')).resolve() == target, 'Partial workspace root differs')
    d.require(git(target, 'branch', '--show-current') == branch, 'Partial workspace branch changed')
    base = metadata['base']
    d.require(git(target, 'rev-parse', 'HEAD') == base and git(root, 'rev-parse', 'refs/heads/' + branch) == base, 'Partial workspace HEAD or branch ref changed')
    d.require(git(root, 'rev-parse', 'HEAD') == base, 'Original checkout moved from recorded workspace base')
    # Git's registration must independently identify this same path, ref and HEAD.
    records = git(root, 'worktree', 'list', '--porcelain', '-z').split('\0\0')
    expected = {'worktree ' + target.as_posix(), 'HEAD ' + base, 'branch refs/heads/' + branch}
    d.require(any(expected <= set(record.split('\0')) for record in records), 'Partial workspace registration differs')
    clean(root)
    clean(target)
    d.require(ownership.lookup(session_id) is None, 'Session already bound; recovery cannot replace a binding')
    capability = ownership.enroll(session_id, target, metadata['id'])
    return {**metadata, 'capability_file': capability, 'recovered': True}


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
    d.require(state['contract'].get('delivery_mode', 'publish') == 'publish', 'Local verification prohibits release preparation, reconciliation and publication')
    policy = state['contract'].get('release', {})
    d.require(policy.get('branch') == 'main' and policy.get('push_authorized') is True, 'Release needs explicit main/remote push authorization')
    d.require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', policy.get('remote', '')), 'Use a configured remote name')
    name = policy.get('version_file', '')
    d.require(isinstance(name, str) and name and not Path(name).is_absolute() and '..' not in Path(name).parts, 'Version file must be repository-relative')
    d.require(d.scoped(name, state['contract']['scope']), 'Version file must be included in scope upfront')
    return policy


def cargo_version(text):
    """Accept one literal workspace version and return its exact source span."""
    try:
        import tomllib
    except ImportError as error:
        raise d.DeliveryError('Cargo workspace versions require Python 3.11+; no dependency is installed automatically') from error
    try:
        data = tomllib.loads(text)
    except ValueError as error:
        raise d.DeliveryError('Invalid or ambiguous Cargo.toml') from error
    workspace = data.get('workspace', {})
    package = workspace.get('package', {}) if isinstance(workspace, dict) else {}
    value = package.get('version') if isinstance(package, dict) else None
    d.require(isinstance(value, str), 'Cargo.toml requires a literal [workspace.package] version')
    # Restrict to an explicit canonical table and single-line unescaped literal.
    # Parsing first rejects duplicate keys/tables; validating the substituted document
    # prevents table-like text in multiline strings from being mistaken for a key.
    header = re.search(r'^\[workspace\.package\][ \t]*(?:#[^\r\n]*)?\r?$', text, re.M)
    d.require(header is not None, 'Use an explicit [workspace.package] version table')
    end = re.search(r'^[ \t]*\[', text[header.end():], re.M)
    stop = header.end() + end.start() if end else len(text)
    matches = list(re.finditer(r'''^[ \t]*version[ \t]*=[ \t]*(["'])([0-9]+\.[0-9]+\.[0-9]+)\1[ \t]*(?:#[^\r\n]*)?\r?$''', text[header.end():stop], re.M))
    d.require(len(matches) == 1 and matches[0][2] == value, 'Only one plain literal Cargo workspace version is supported')
    match = matches[0]
    span = (header.end() + match.start(2), header.end() + match.end(2))
    probe = text[:span[0]] + '0.0.0-veera-probe' + text[span[1]:]
    expected = copy.deepcopy(data)
    expected['workspace']['package']['version'] = '0.0.0-veera-probe'
    d.require(tomllib.loads(probe) == expected, 'Ambiguous Cargo workspace version location')
    return value, span


def version_text(path, text):
    if path.name == 'Cargo.toml':
        value = cargo_version(text)[0]
    else:
        value = json.loads(text)['version'] if path.suffix == '.json' else text.strip()
    d.require(isinstance(value, str), 'Version must be a plain x.y.z string')
    match = re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value)
    d.require(match is not None, 'Only plain x.y.z patch versions supported; complex release schemes need a project adapter')
    return value, '.'.join([match[1], match[2], str(int(match[3]) + 1)])


def version_value(path):
    text = path.read_bytes().decode('utf-8') if path.name == 'Cargo.toml' else path.read_text()
    return version_text(path, text)


def write_version(path, value):
    if path.name == 'Cargo.toml':
        text = path.read_bytes().decode('utf-8')
        _, (start, end) = cargo_version(text)
        path.write_bytes((text[:start] + value + text[end:]).encode('utf-8'))
    elif path.suffix == '.json':
        data = json.loads(path.read_text())
        data['version'] = value
        path.write_text(json.dumps(data, indent=2) + '\n')
    else:
        path.write_text(value + '\n')


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
        main_version = version_text(path, main_text)[0]
        d.require(old == main_version, 'Task must not modify the release version; patch increment is based on integrated main')
        write_version(path, new)
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
        release_policy(state)
        d.require(not state.get('push_attempted'), 'Cannot retry/reconcile automatically after a push attempt')
        d.require(state.get('release_prepared') and reason.strip(), 'Reconciliation needs a prepared release and new evidence')
        d.require(not state.get('running'), 'Check still running')
        d.require(state['repairs'] < d.repair_limit(state), 'Repair ceiling exhausted')
        plan = state['release_prepared']
        path = Path(root) / plan['version_file']
        d.require(version_value(path)[0] == plan['version_to'], 'Version differs from prepared value; inspect before reconciliation')
        write_version(path, plan['version_from'])
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
        import check_reporting
        check_reporting.validate_result(root, state, spec, result, d.digest)
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
