"""Loopback-only status server. No external assets, source files or log serving."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import threading
import time
import re
import webbrowser
from urllib.request import build_opener, ProxyHandler
from urllib.parse import urlsplit
from delivery import status, stop, TERMINAL, DeliveryError, locked, atomic, storage
from platform_runtime import file_lock
import dashboard_documents


PAGE = Path(__file__).resolve().parent.parent / 'web' / 'index.html'


def create_server(root, port=0):
    token = secrets.token_urlsafe(32)
    run_id = status(root)['run_id']

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # URLs contain the local capability token.

        def reply(self, code, body, content_type='application/json'):
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid(self):
            host = f'127.0.0.1:{self.server.server_port}'
            return self.headers.get('Host') == host and urlsplit(self.path).path.startswith('/' + token + '/')

        def do_GET(self):
            if not self.valid():
                return self.reply(404, b'{}')
            path = urlsplit(self.path).path.removeprefix('/' + token + '/')
            if path in ('', 'index.html'):
                return self.reply(200, PAGE.read_bytes(), 'text/html; charset=utf-8')
            if path in ('app.js', 'documents.js', 'style.css'):
                return self.reply(200, (PAGE.parent / path).read_bytes(), 'application/javascript' if path.endswith('.js') else 'text/css')
            if path == 'health':
                try:
                    if status(root)['run_id'] != run_id:
                        return self.reply(410, b'{"error":"run replaced"}')
                    return self.reply(200, json.dumps({'run_id': run_id}).encode())
                except (OSError, ValueError, KeyError, DeliveryError):
                    return self.reply(503, b'{}')
            if path == 'status':
                try:
                    state = status(root)
                    if state['run_id'] != run_id:
                        return self.reply(410, b'{"error":"run replaced"}')
                    # Never expose captured command output or full source hashes.
                    view = {key: state[key] for key in ('mode', 'request', 'status', 'phase', 'started_at', 'updated_at', 'deadline', 'repairs', 'contract', 'checks', 'events', 'usage')}
                    view['soft_deadline'] = state.get('soft_deadline')
                    view['replan_required'] = state.get('replan_required', False)
                    view['release_prepared'] = state.get('release_prepared')
                    view['push_attempted'] = state.get('push_attempted')
                    view['memory_revision'] = state.get('context', {}).get('revision', 0)
                    view['blockers'] = [{'id': b['id'], 'target': b['target'], 'status': b['status'], 'attempts': len(b['attempts']), 'limit': b['limit']} for b in state.get('blockers', {}).values()]
                    view['now'] = time.time()
                    view['running'] = state.get('running')
                    return self.reply(200, json.dumps(view).encode())
                except (OSError, ValueError, KeyError, DeliveryError) as error:
                    return self.reply(503, json.dumps({'error': type(error).__name__}).encode())
            if path == 'documents' or path.startswith('document/'):
                try:
                    state = status(root)
                    if state['run_id'] != run_id:
                        return self.reply(410, b'{"error":"run replaced"}')
                    value = dashboard_documents.catalog() if path == 'documents' else dashboard_documents.document(path.removeprefix('document/'), state)
                    return self.reply(200, json.dumps(value).encode())
                except KeyError:
                    return self.reply(404, b'{"error":"document not found"}')
                except (OSError, ValueError, DeliveryError):
                    return self.reply(503, b'{"error":"document unavailable"}')
            self.reply(404, b'{}')

        def do_POST(self):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid() or self.headers.get('Origin') != origin or self.headers.get('X-Delivery-Control') != 'stop':
                return self.reply(403, b'{}')
            if urlsplit(self.path).path != '/' + token + '/stop':
                return self.reply(404, b'{}')
            try:
                stop(root, 'Stopped from local dashboard', expected_run_id=run_id)
            except (OSError, DeliveryError):
                return self.reply(410, b'{"error":"run unavailable or replaced"}')
            self.reply(200, b'{"status":"user-stopped"}')

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.run_id = run_id
    return server, f'http://127.0.0.1:{server.server_port}/{token}/'


def info(root):
    """Return only this run's validated, live URL; never discover other tasks."""
    state = status(root)
    with locked(root) as directory:
        path = directory / 'dashboard.json'
        result = {'status': 'not-started', 'dashboard_url': None, 'record_path': str(path)}
        if not path.exists():
            return result
        record = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(record, dict):
        raise ValueError('Invalid saved dashboard record')
    if record.get('run_id') != state['run_id']:
        return {**result, 'status': 'stale'}
    url = record.get('dashboard_url', '')
    if not isinstance(url, str) or not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}/[A-Za-z0-9_-]{43}/', url):
        raise ValueError('Invalid saved dashboard address')
    try:
        with build_opener(ProxyHandler({})).open(url + 'health', timeout=1) as response:
            live = json.loads(response.read(4096)).get('run_id') == state['run_id']
    except (OSError, ValueError):
        live = False
    return {**result, 'status': 'running' if live else 'not-running',
            'dashboard_url': url if live else None,
            'browser_open_requested': record.get('browser_open_requested', False)}


def serve(root, port=0, open_browser=True):
    # One server per task; a repeated request reuses its existing address.
    directory = storage(root)
    try:
        with file_lock(directory / 'dashboard-server.lock', blocking=False):
            return _serve(root, port, open_browser)
    except BlockingIOError:
        existing = info(root)
        if open_browser and existing['dashboard_url']:
            try:
                webbrowser.open(existing['dashboard_url'], new=2)
            except Exception:
                pass  # The validated URL remains the supported fallback.
        print(json.dumps(existing), flush=True)


def _serve(root, port=0, open_browser=True):
    status(root)  # Fail early rather than serve a broken dashboard.
    server, url = create_server(root, port)
    record = {'run_id': server.run_id, 'dashboard_url': url, 'pid': os.getpid(),
              'started_at': time.time(), 'browser_open_requested': open_browser}
    with locked(root) as directory:
        atomic(directory / 'dashboard.json', record)
    print(json.dumps({'dashboard_url': url, 'record_path': str(directory / 'dashboard.json'),
                      'binding': 'loopback', 'browser_open_requested': open_browser,
                      'auto_shutdown': '60 seconds after terminal state'}), flush=True)

    def monitor():
        terminal_since = None
        while True:
            time.sleep(1)
            try:
                state = status(root)
                if state['run_id'] != server.run_id:
                    server.shutdown()
                    return
                if state['status'] in TERMINAL:
                    terminal_since = terminal_since or time.time()
                    if time.time() - terminal_since >= 60:
                        server.shutdown()
                        return
            except Exception:
                server.shutdown()
                return

    threading.Thread(target=monitor, daemon=True).start()
    if open_browser:
        def open_view():
            try:
                webbrowser.open(url, new=2)
            except Exception:
                pass  # Headless hosts can open the printed URL through native UI tools.
        threading.Thread(target=open_view, daemon=True).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()
