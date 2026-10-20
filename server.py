"""Single-user career workspace. Python standard library; bind locally by default."""
import json
import base64
import hmac
import os
import sqlite3
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('CAREER_DB', str(ROOT / '.data' / 'career.sqlite3')))
SEED = {
    'profile': {'name': 'there', 'summary': 'Build your next career chapter.', 'facts': '', 'confirmed': False},
    'jobs': [], 'stories': [], 'sessions': [],
}
AUTH_USER = os.environ.get('CAREER_USER', 'owner')
AUTH_PASSWORD = os.environ.get('CAREER_PASSWORD', '')


def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute('CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
    conn.execute('INSERT OR IGNORE INTO workspace VALUES (1, ?)', (json.dumps(SEED),))
    conn.commit()
    return conn

def validate(data):
    if not isinstance(data, dict) or set(data) != set(SEED):
        return False
    return (isinstance(data['profile'], dict) and isinstance(data['profile'].get('name'), str)
            and isinstance(data['profile'].get('facts'), str) and isinstance(data['profile'].get('summary'), str)
            and isinstance(data['profile'].get('confirmed'), bool)
            and all(isinstance(data[k], list) and all(isinstance(x, dict) for x in data[k]) for k in ('jobs', 'stories', 'sessions')))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'static'), **kwargs)

    def authenticated(self):
        if not AUTH_PASSWORD:
            return True
        expected = 'Basic ' + base64.b64encode((AUTH_USER + ':' + AUTH_PASSWORD).encode()).decode()
        if hmac.compare_digest(self.headers.get('Authorization', ''), expected):
            return True
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Next Chapter", charset="UTF-8"')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        return False

    def do_HEAD(self):
        if self.authenticated():
            super().do_HEAD()

    def do_GET(self):
        if not self.authenticated():
            return
        if self.path == '/api/workspace':
            with connection() as conn:
                body = conn.execute('SELECT body FROM workspace WHERE id=1').fetchone()[0].encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith('/api/'):
            self.send_error(404)
        else:
            super().do_GET()

    def do_PUT(self):
        if not self.authenticated():
            return
        if self.path != '/api/workspace':
            return self.send_error(404)
        # Reject browser requests originating on another site. No public hosting/auth in v1.
        origin = self.headers.get('Origin')
        if origin and origin not in ('http://' + self.headers.get('Host', ''), 'https://' + self.headers.get('Host', '')):
            return self.send_error(403)
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.send_error(415)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 2_000_000:
                return self.send_error(413)
            data = json.loads(self.rfile.read(length))
            if not validate(data):
                return self.send_error(400, 'Invalid workspace structure')
        except (ValueError, UnicodeDecodeError):
            return self.send_error(400)
        with connection() as conn:
            conn.execute('UPDATE workspace SET body=? WHERE id=1', (json.dumps(data),))
        self.send_response(204)
        self.end_headers()

if __name__ == '__main__':
    host, port = os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '8000'))
    if host not in ('127.0.0.1', 'localhost', '::1') and len(AUTH_PASSWORD) < 16:
        raise SystemExit('Set CAREER_PASSWORD to at least 16 characters before exposing the server.')
    connection().close()
    print(f'Career workspace listening on {host}:{port}', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
