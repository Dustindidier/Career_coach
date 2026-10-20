import base64
import copy
import importlib.util
import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('career_server', Path(__file__).parents[1] / 'server.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage_patch = patch.multiple(app, SUPABASE_URL='', SUPABASE_KEY='', AUTH_PASSWORD='', GEMINI_KEY='')
        cls.storage_patch.start()
        cls.tmp = tempfile.TemporaryDirectory()
        app.DB = Path(cls.tmp.name) / 'test.sqlite3'
        app.connection().close()
        cls.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()
        cls.storage_patch.stop()

    def get(self):
        with urllib.request.urlopen(self.url+'/api/workspace') as r:
            return json.load(r), r.headers['ETag']

    def put(self, data, etag, origin=None):
        headers={'Content-Type':'application/json'}
        if etag is not None: headers['If-Match']=etag
        if origin: headers['Origin']=origin
        return urllib.request.urlopen(urllib.request.Request(self.url+'/api/workspace', data=json.dumps(data).encode(), headers=headers, method='PUT'))

    def post(self, path, data):
        return urllib.request.urlopen(urllib.request.Request(self.url+path, data=json.dumps(data).encode(), headers={'Content-Type':'application/json'}, method='POST'))

    def test_roundtrip_persists_and_revision_advances(self):
        _, etag=self.get()
        data=copy.deepcopy(app.SEED)
        data['stories'].append({'id':'test', 'title':'Safety example', 'tags':'review', 'situation':'A discrepancy', 'action':'Clarified facts', 'outcome':'Information corrected'})
        with self.put(data,etag) as r:
            self.assertEqual(r.status,204)
            self.assertEqual(int(r.headers['ETag'].strip('"')),int(etag.strip('"'))+1)
        self.assertEqual(self.get()[0],data)
        with app.connection() as c:
            self.assertEqual(json.loads(c.execute('SELECT body FROM workspace').fetchone()[0]),data)

    def test_two_devices_cannot_overwrite_each_other(self):
        data, etag=self.get()
        first=copy.deepcopy(data);first['profile']['name']='First device'
        second=copy.deepcopy(data);second['profile']['name']='Second device'
        with self.put(first,etag): pass
        with self.assertRaises(urllib.error.HTTPError) as cm:self.put(second,etag)
        self.assertEqual(cm.exception.code,409)
        self.assertEqual(self.get()[0]['profile']['name'],'First device')

    def test_simultaneous_writers_only_one_succeeds(self):
        data,etag=self.get()
        barrier=threading.Barrier(2)
        def save(name):
            value=copy.deepcopy(data);value['profile']['name']=name;barrier.wait()
            try:
                with self.put(value,etag) as r:return r.status
            except urllib.error.HTTPError as e:return e.code
        with ThreadPoolExecutor(2) as executor:
            results=list(executor.map(save,['A','B']))
        self.assertEqual(sorted(results),[204,409])

    def test_old_clients_cannot_bypass_revision_check(self):
        before,_=self.get()
        with self.assertRaises(urllib.error.HTTPError) as cm:self.put(before,None)
        self.assertEqual(cm.exception.code,428)
        self.assertEqual(self.get()[0],before)

    def test_invalid_import_preserves_existing_data(self):
        data,etag=self.get()
        invalid=copy.deepcopy(data);invalid['stories']=[{'id':'broken'}]
        with self.assertRaises(urllib.error.HTTPError) as cm:self.put(invalid,etag)
        self.assertEqual(cm.exception.code,400)
        self.assertEqual(self.get()[0],data)

    def test_cross_origin_write_rejected(self):
        data,etag=self.get()
        with self.assertRaises(urllib.error.HTTPError) as cm:self.put(data,etag,'https://other.example')
        self.assertEqual(cm.exception.code,403)

    def test_authentication_protects_workspace_and_coach(self):
        with patch.object(app,'AUTH_PASSWORD','test-password-long-enough'):
            for path in ['/api/workspace','/api/capabilities']:
                with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(self.url+path)
                self.assertEqual(cm.exception.code,401)
            with self.assertRaises(urllib.error.HTTPError) as cm:self.post('/api/coach',{})
            self.assertEqual(cm.exception.code,401)
            auth='Basic '+base64.b64encode((app.AUTH_USER+':'+app.AUTH_PASSWORD).encode()).decode()
            req=urllib.request.Request(self.url+'/api/workspace',headers={'Authorization':auth})
            with urllib.request.urlopen(req) as r:self.assertIn('profile',json.load(r))

    def test_cloud_compare_and_swap_uses_revision_filter(self):
        with patch.object(app,'SUPABASE_URL','https://example.supabase.co'):
            with patch.object(app,'cloud_request',return_value=[{'body':app.SEED,'revision':7}]):
                self.assertEqual(app.read_snapshot(),(app.SEED,7))
            with patch.object(app,'cloud_request',return_value=[{'revision':8}]) as remote:
                self.assertEqual(app.write_workspace(app.SEED,7),8)
                self.assertEqual(remote.call_args.args[2],'?id=eq.1&revision=eq.7')
                self.assertEqual(remote.call_args.kwargs['prefer'],'return=representation')
            with patch.object(app,'cloud_request',return_value=[]):
                with self.assertRaises(app.Conflict):app.write_workspace(app.SEED,7)

    def test_storage_failure_is_not_reported_as_saved(self):
        with patch.object(app,'read_snapshot',side_effect=RuntimeError('unavailable')):
            with self.assertRaises(urllib.error.HTTPError) as cm:self.get()
            self.assertEqual(cm.exception.code,503)

    def test_health_check_exposes_no_workspace(self):
        with patch.object(app,'AUTH_PASSWORD','test-password-long-enough'):
            with urllib.request.urlopen(self.url+'/healthz') as r:self.assertEqual(json.load(r),{'status':'ok'})

    def test_guided_coach_requires_no_model_call(self):
        with patch.object(app,'ai_coach') as ai:
            with self.post('/api/coach',{'turn':0,'mode':'recruiter','job':{'title':'Safety Nurse','company':'Example'}}) as r:result=json.load(r)
            self.assertIn('Safety Nurse',result['question']);self.assertEqual(result['engine'],'guided');ai.assert_not_called()

    def test_ai_quota_error_falls_back_to_free_guided_mode(self):
        with patch.object(app,'GEMINI_KEY','fake'),patch.object(app,'ai_coach',side_effect=RuntimeError('quota')):
            with self.post('/api/coach',{'engine':'gemini','turn':1,'mode':'recruiter','answer':'A short answer','job':{}}) as r:result=json.load(r)
            self.assertEqual(result['engine'],'guided');self.assertIn('quota',result['warning'])

    def test_analysis_returns_only_source_passages(self):
        text='Must hold an active RN license.\nPrepare safety narratives and communicate with sites.\nResearch experience preferred.'
        with self.post('/api/analyze',{'posting':text}) as r:result=json.load(r)
        self.assertEqual(len(result['requirements']),3)
        self.assertTrue(all(x['text'] in text and not x['reviewed'] for x in result['requirements']))

    def test_malformed_coach_payload_is_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:self.post('/api/coach',{'turn':0,'mode':'recruiter','job':{'requirements':[42]}})
        self.assertEqual(cm.exception.code,400)

if __name__=='__main__':unittest.main()
