"""Loopback-only status server. No external assets, source files or log serving."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit
from delivery import status, stop, TERMINAL, DeliveryError


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
            if path in ('app.js', 'style.css'):
                return self.reply(200, (PAGE.parent / path).read_bytes(), 'application/javascript' if path.endswith('.js') else 'text/css')
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


def serve(root, port=0):
    status(root)  # Fail early rather than serve a broken dashboard.
    server, url = create_server(root, port)
    print(json.dumps({'dashboard_url': url, 'binding': 'loopback', 'auto_shutdown': '60 seconds after terminal state'}), flush=True)

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
    try:
        server.serve_forever()
    finally:
        server.server_close()
