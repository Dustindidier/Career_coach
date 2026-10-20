import copy
import importlib.util
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error
from pathlib import Path

spec = importlib.util.spec_from_file_location('career_server', Path(__file__).parents[1] / 'server.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        app.DB = Path(cls.tmp.name) / 'test.sqlite3'
        cls.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def request(self, data=None, origin=None):
        headers={'Content-Type': 'application/json'}
        if origin: headers['Origin'] = origin
        return urllib.request.urlopen(urllib.request.Request(self.url+'/api/workspace', data=json.dumps(data).encode() if data is not None else None, headers=headers, method='PUT' if data is not None else 'GET'))

    def test_roundtrip_persists_to_disk(self):
        data = copy.deepcopy(app.SEED)
        data['stories'].append({'id':'test', 'title':'A real clinical example'})
        with self.request(data) as r: self.assertEqual(r.status, 204)
        with self.request() as r: self.assertEqual(json.load(r), data)
        # New SQLite connection proves this is not just server memory.
        with app.connection() as c:
            self.assertEqual(json.loads(c.execute('SELECT body FROM workspace').fetchone()[0]), data)

    def test_invalid_state_does_not_overwrite(self):
        with self.request() as r: before=json.load(r)
        with self.assertRaises(urllib.error.HTTPError) as cm: self.request({'profile':{}})
        self.assertEqual(cm.exception.code,400)
        with self.request() as r: self.assertEqual(json.load(r),before)

    def test_cross_origin_write_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as cm: self.request(app.SEED,'https://unrelated.example')
        self.assertEqual(cm.exception.code,403)

    def test_authentication_protects_read_and_write(self):
        old = app.AUTH_PASSWORD
        app.AUTH_PASSWORD = 'test-password-long-enough'
        try:
            for data in (None, app.SEED):
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    self.request(data)
                self.assertEqual(cm.exception.code, 401)
            import base64
            token = base64.b64encode((app.AUTH_USER + ':' + app.AUTH_PASSWORD).encode()).decode()
            req = urllib.request.Request(self.url+'/api/workspace', headers={'Authorization':'Basic '+token})
            with urllib.request.urlopen(req) as r:
                self.assertIn('profile', json.load(r))
        finally:
            app.AUTH_PASSWORD = old

    def test_cloud_storage_initializes_and_updates_workspace(self):
        with patch.object(app, 'SUPABASE_URL', 'https://example.supabase.co'):
            with patch.object(app, 'cloud_request', side_effect=[[], None, [{'body': app.SEED}]]) as remote:
                self.assertEqual(app.read_workspace(), app.SEED)
                self.assertEqual(remote.call_args_list[1].args, ('POST', {'id': 1, 'body': app.SEED}))
            with patch.object(app, 'cloud_request', side_effect=[[{'body': app.SEED}], None]) as remote:
                app.write_workspace(app.SEED)
                self.assertEqual(remote.call_args_list[-1].args, ('PATCH', {'body': app.SEED}, '?id=eq.1'))

    def test_storage_failure_returns_503(self):
        with patch.object(app, 'read_workspace', side_effect=RuntimeError('storage unavailable')):
            with self.assertRaises(urllib.error.HTTPError) as cm:
                self.request()
            self.assertEqual(cm.exception.code, 503)

    def test_frontend_served(self):
        with urllib.request.urlopen(self.url+'/') as r:
            self.assertIn(b'Next Chapter',r.read())

if __name__ == '__main__': unittest.main()
