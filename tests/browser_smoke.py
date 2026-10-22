#!/usr/bin/env python3
"""Real local browser smoke test; no model calls or external requests."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import delivery
import dashboard


def main():
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        raise SystemExit('BLOCKED: Chrome/Chromium is not installed')
    artifacts = Path(__file__).resolve().parents[1] / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / 'app'
        root.mkdir()
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        (root / 'app.py').write_text('value = 1\n')
        contract = {'scope': ['app.py'], 'criteria': [{'id': 'C1', 'text': 'Browser shows live state', 'checks': ['unit']}], 'checks': [{'id': 'unit', 'kind': 'test', 'argv': [sys.executable, '-c', "print('Ran 1 test')"], 'count_pattern': r'Ran (\d+) test'}], 'non_goals': ['No deployment']}
        delivery.init(root, 'fix', '<img src=x onerror=alert(1)> Visual smoke fixture', contract, 2)
        server, url = dashboard.create_server(root)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            result = subprocess.run([chrome, '--headless', '--disable-gpu', '--no-proxy-server', '--no-first-run', '--disable-background-networking', '--disable-component-update', '--disable-extensions', '--user-data-dir=' + str(Path(temp) / 'browser'), '--window-size=1280,900', '--virtual-time-budget=5000', '--screenshot=' + str(artifacts / 'dashboard.png'), '--dump-dom', url], capture_output=True, text=True, timeout=30)
            (artifacts / 'browser.stderr.log').write_text(result.stderr)
            (artifacts / 'dashboard.dom.html').write_text(result.stdout)
            assert result.returncode == 0, 'Chrome failed; see browser.stderr.log'
            assert 'Live · updated' in result.stdout, 'Dashboard did not fetch live state'
            assert 'FIX: &lt;img' in result.stdout, 'Request must render as text, never HTML'
            assert 'unit: not run' in result.stdout, 'Unrun checks must not appear passed'
            assert (artifacts / 'dashboard.png').stat().st_size > 1000, 'Screenshot missing'
            print(json.dumps({'status': 'passed', 'checks': ['live status rendered', 'untrusted request escaped', 'not-run status', 'desktop screenshot captured'], 'screenshot': str(artifacts / 'dashboard.png')}))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
