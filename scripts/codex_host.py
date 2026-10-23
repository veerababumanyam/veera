"""Opt-in native hooks/list inspection; no chat, model, trust or config writes."""
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

PLUGIN = 'veera@veera-plugins'


def summarize(response, package):
    if not isinstance(response, dict) or 'error' in response:
        raise ValueError('Codex rejected the read-only hooks/list request')
    entries = response.get('result', {}).get('data')
    if not isinstance(entries, list) or len(entries) != 1:
        raise ValueError('Unexpected hooks/list response for the requested project')
    entry = entries[0]
    if not isinstance(entry, dict) or not isinstance(entry.get('hooks'), list):
        raise ValueError('Invalid hooks/list entry')
    hooks = []
    expected = (Path(package) / 'adapters/codex/hooks.json').resolve()
    for item in entry['hooks']:
        if not isinstance(item, dict) or item.get('pluginId') != PLUGIN:
            continue
        hooks.append({'event': item.get('eventName'), 'enabled': item.get('enabled') is True,
                      'trust': item.get('trustStatus'), 'source': item.get('sourcePath'),
                      'matches_package': isinstance(item.get('sourcePath'), str) and Path(item['sourcePath']).resolve() == expected})
    events = {item['event'] for item in hooks}
    status = ('missing' if not {'preToolUse', 'userPromptSubmit'} <= events else
              'disabled' if not all(item['enabled'] for item in hooks) else
              'review-required' if not all(item['trust'] in ('trusted', 'managed') for item in hooks) else
              'package-mismatch' if not all(item['matches_package'] for item in hooks) else 'ready')
    return {'status': status, 'hooks': hooks, 'load_error_count': len(entry.get('errors', [])),
            'warning_count': len(entry.get('warnings', [])), 'trust_changed': False,
            'scope': 'Fresh host configuration for this project; not an existing chat reload or live hook execution'}


def inspect(package, cwd, executable=None, timeout=15):
    """Ask a short-lived metadata-only server; never launch a model or session."""
    from model_router import find_codex
    executable = executable or find_codex()
    if not executable:
        return {'status': 'unavailable', 'reason': 'Codex executable not found', 'trust_changed': False}
    responses = queue.Queue()
    process = None
    try:
        process = subprocess.Popen([executable, '--no-daemon', 'app-server', '--stdio'],
                                   cwd=str(Path(cwd).resolve(strict=True)), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   text=True, encoding='utf-8',
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        def read():
            while True:
                line = process.stdout.readline(512 * 1024)
                if not line:
                    responses.put(None)
                    return
                if not line.endswith('\n'):
                    responses.put(None)
                    return
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if isinstance(item, dict) and item.get('id') in (1, 2):
                    responses.put(item)

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        deadline = time.monotonic() + timeout

        def send(item):
            process.stdin.write(json.dumps(item) + '\n')
            process.stdin.flush()

        def receive(identifier):
            while True:
                item = responses.get(timeout=max(0, deadline - time.monotonic()))
                if item is None:
                    raise ValueError('Codex metadata server closed before returning hooks')
                if item.get('id') == identifier:
                    return item

        send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'veera_hook_diagnostic', 'version': '1'},
                                                       'capabilities': {'experimentalApi': True}}})
        if 'result' not in receive(1):
            raise ValueError('Codex metadata initialization failed')
        send({'method': 'initialized', 'params': {}})
        send({'id': 2, 'method': 'hooks/list', 'params': {'cwds': [str(Path(cwd).resolve())]}})
        return summarize(receive(2), package)
    except (OSError, ValueError, TypeError, AttributeError, queue.Empty):
        return {'status': 'unavailable', 'reason': 'Read-only host query failed or timed out; trust is unknown', 'trust_changed': False}
    finally:
        if process is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.terminate()  # Only the diagnostic's own metadata child.
                process.wait(timeout=2)
            reader.join(timeout=1)
            process.stdout.close()
