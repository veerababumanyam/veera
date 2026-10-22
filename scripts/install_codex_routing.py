#!/usr/bin/env python3
"""Install only Veera's two personal Codex roles; preserve all other settings."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tomllib
import uuid

ROOT = Path(__file__).resolve().parents[1]
BEGIN = '# BEGIN VEERA NATIVE ROUTING'
END = '# END VEERA NATIVE ROUTING'
MARK = '# Managed by Veera native routing installer.\n'


def install(home):
    home = Path(home).resolve()
    config = home / 'config.toml'
    if config.is_symlink():
        raise ValueError('Refusing symlink config target')
    original = config.read_text(encoding='utf-8') if config.exists() else ''
    existing = tomllib.loads(original)
    if existing.get('features', {}).get('multi_agent') is False or existing.get('agents', {}).get('enabled') is False:
        raise ValueError('Native subagents are explicitly disabled; resolve the host policy before installing routing')
    managed = re.compile(re.escape(BEGIN) + r'\n.*?\n' + re.escape(END) + r'\n?', re.S)
    if original.count(BEGIN) != original.count(END) or original.count(BEGIN) > 1:
        raise ValueError('Invalid managed routing block; no settings changed')
    unmanaged = managed.sub('', original)
    base = tomllib.loads(unmanaged)
    targets = []
    runtime = home / 'veera-routing-runtime.json'
    if runtime.is_symlink():
        raise ValueError('Refusing symlink runtime configuration')
    if runtime.exists():
        if json.loads(runtime.read_text(encoding='utf-8')).get('managed_by') != 'veera-native-routing':
            raise ValueError('Unmanaged routing runtime configuration; no settings changed')
    block = [BEGIN]
    for tier in ('light', 'important'):
        name = 'veera_' + tier
        if name in base.get('agents', {}):
            raise ValueError('Existing unmanaged role conflicts with ' + name)
        path = home / 'agents' / (name + '.toml')
        content = MARK + (ROOT / 'adapters/codex/agents' / path.name).read_text(encoding='utf-8')
        if path.exists() and not path.read_text(encoding='utf-8').startswith(MARK):
            raise ValueError('Unmanaged agent file conflicts with ' + str(path))
        if path.is_symlink():
            raise ValueError('Refusing symlink agent target')
        targets.append((path, content))
        block += ['', '[agents.' + name + ']',
                  'description = ' + json.dumps('Veera ' + tier + ' findings-only delegate'),
                  'config_file = ' + json.dumps(str(path).replace('\\', '/'))]
    block += ['', END, '']
    updated = unmanaged.rstrip() + '\n\n' + '\n'.join(block)
    tomllib.loads(updated)
    backup = None
    if updated != original:
        home.mkdir(parents=True, exist_ok=True)
        if config.exists():
            backup = home / ('config.toml.veera-backup-' + uuid.uuid4().hex)
            shutil.copy2(config, backup)
    for path, content in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding='utf-8') != content:
            path.write_text(content, encoding='utf-8')
    runtime.write_text(json.dumps({'managed_by': 'veera-native-routing', 'python_executable': sys.executable}, indent=2) + '\n', encoding='utf-8')
    if updated != original:
        config.write_text(updated, encoding='utf-8')
    return {'installed_roles': [str(p) for p, _ in targets], 'config_backup': str(backup) if backup else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-home', type=Path, default=Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))))
    args = parser.parse_args()
    print(json.dumps(install(args.codex_home)))
