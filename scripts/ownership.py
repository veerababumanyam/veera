"""Explicit session routing. Cooperative isolation, not a same-UID sandbox."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets

REGISTRY = None  # Explicit test injection only; production uses host persistent data.


def registry():
    if REGISTRY is not None:
        return REGISTRY
    base = os.environ.get('CLAUDE_PLUGIN_DATA')
    host = os.environ.get('VEERA_HOST', 'claude')
    if not base or not Path(base).is_absolute() or host not in ('claude', 'codex'):
        raise ValueError('Host persistent data directory and supported host are required')
    path = Path(base) / 'veera-v1' / host / 'sessions'
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Persistent data must not traverse symlinks')
    return path


def session_key(session_id):
    if not isinstance(session_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', session_id):
        raise ValueError('An actual host session ID is required')
    return hashlib.sha256(session_id.encode()).hexdigest()


def lookup(session_id):
    path = registry() / (session_key(session_id) + '.json')
    if registry().is_symlink() or path.is_symlink():
        raise ValueError('Unsafe session routing path')
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    if record.get('session_id') != session_id:
        raise ValueError('Session routing identity mismatch')
    return record


def enroll(session_id, root, workspace_id):
    key = session_key(session_id)
    if lookup(session_id) is not None:
        raise ValueError('Session is already bound; do not adopt or overwrite another task')
    registry().mkdir(mode=0o700, parents=True, exist_ok=True)
    path = registry() / (key + '.json')
    record = {'session_id': session_id, 'root': str(Path(root).resolve()), 'workspace_id': workspace_id, 'capability': secrets.token_urlsafe(32)}
    # Exclusive creation prevents concurrent enrollment replacing an owner.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(record, stream)
    return str(path)


def authorize(session_id, root, capability_file):
    record = lookup(session_id)
    if record is None:
        raise ValueError('Session is not enrolled; no task access performed')
    if Path(root).resolve() != Path(record['root']).resolve():
        raise ValueError('Requested root is not this session task')
    expected = registry() / (session_key(session_id) + '.json')
    if not capability_file or Path(capability_file).resolve() != expected.resolve():
        raise ValueError('Owner capability file required')
    # Only now inspect owned workspace metadata, never a foreign run.
    metadata = Path(record['root']) / '.veera' / 'workspace.json'
    if metadata.is_symlink() or metadata.parent.is_symlink():
        raise ValueError('Unsafe owned workspace metadata')
    value = json.loads(metadata.read_text())
    if value.get('id') != record['workspace_id'] or value.get('session_id') != session_id:
        raise ValueError('Owned workspace identity changed')
    return record


def migrate(session_id, root, legacy_file):
    """Copy one explicit quiescent owner's legacy record; never scan or delete."""
    key = session_key(session_id)
    old = Path(legacy_file)
    if old.name != key + '.json' or any(p.is_symlink() for p in (old, *old.parents)):
        raise ValueError('Legacy path must name this exact owner record without symlinks')
    record = json.loads(old.read_text())
    if record.get('session_id') != session_id or not record.get('root') or Path(record['root']).resolve() != Path(root).resolve():
        raise ValueError('Legacy owner/task mismatch')
    metadata = Path(root) / '.veera/workspace.json'
    if metadata.is_symlink() or metadata.parent.is_symlink():
        raise ValueError('Unsafe workspace metadata')
    meta = json.loads(metadata.read_text())
    if meta.get('id') != record.get('workspace_id') or meta.get('session_id') != session_id:
        raise ValueError('Legacy workspace identity mismatch')
    existing = lookup(session_id)
    if existing is not None:
        if existing != record:
            raise ValueError('Conflicting persistent owner record')
        return {'status': 'already-migrated', 'capability_file': str(registry() / (key + '.json'))}
    registry().mkdir(mode=0o700, parents=True, exist_ok=True)
    target = registry() / (key + '.json')
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(record, stream)
    return {'status': 'migrated', 'capability_file': str(target), 'legacy_preserved': True}


def unbind(session_id, root, capability_file):
    """Release only this routing record after completion, never another session."""
    record = authorize(session_id, root, capability_file)
    state = json.loads((Path(record['root']) / '.veera/state.json').read_text())
    if state.get('status') != 'complete':
        raise ValueError('Only a completed task can release its session binding')
    path = registry() / (session_key(session_id) + '.json')
    path.unlink()
    return {'status': 'unbound', 'session_id': session_id}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Explicit owner-only routing migration; stop the old owner before cutover')
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--legacy-file', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(migrate(args.session_id, args.root, args.legacy_file)))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, str(error) + '\n')
