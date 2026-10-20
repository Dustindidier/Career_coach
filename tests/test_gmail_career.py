import base64
import copy
import json
import time
import unittest
from email import policy
from email.parser import BytesParser
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from gmail import Gmail, start_oauth, verify_oauth, encode, normalize_message, alert_links, context_hints
from career import search_plan, tailor

class OAuthTests(unittest.TestCase):
    def test_pkce_cookie_and_state_binding(self):
        url,cookie=start_oauth('client','https://example.com/oauth/gmail/callback','private-signing-key')
        query=parse_qs(urlsplit(url).query)
        verifier=verify_oauth(cookie,query['state'][0],'private-signing-key')
        import hashlib
        self.assertEqual(query['code_challenge'][0],encode(hashlib.sha256(verifier.encode()).digest()))
        self.assertEqual(query['code_challenge_method'],['S256'])
        self.assertNotIn(verifier,url)
        self.assertIn('gmail.readonly',query['scope'][0])

    def test_tampered_expired_or_foreign_states_fail(self):
        url,cookie=start_oauth('client','https://example.com/callback','key')
        state=parse_qs(urlsplit(url).query)['state'][0]
        for changed,key,value in [(cookie,'wrong-key',state),(cookie,'key','wrong-state'),(cookie+'x','key',state)]:
            with self.assertRaises(ValueError):verify_oauth(changed,value,key)
        with patch('gmail.time.time',return_value=time.time()+1000):
            with self.assertRaises(ValueError):verify_oauth(cookie,state,'key')

class GmailTests(unittest.TestCase):
    def setUp(self):
        self.tokens={'access_token':'fake-access','refresh_token':'fake-refresh','expires_at':time.time()+3600}
        self.client=Gmail(lambda:copy.deepcopy(self.tokens),self.save,lambda:None,'client','secret','https://example.com/callback')
    def save(self,value):self.tokens=value

    def test_refresh_preserves_refresh_token(self):
        self.tokens['expires_at']=0
        with patch('gmail.google_token',return_value={'access_token':'refreshed','expires_in':3600}) as token:
            result=self.client.access()
        self.assertEqual(result['refresh_token'],'fake-refresh')
        self.assertEqual(result['access_token'],'refreshed')
        self.assertEqual(token.call_args.args[0]['grant_type'],'refresh_token')

    def test_consent_requires_both_scopes_and_offline_access(self):
        with patch('gmail.google_token',return_value={'access_token':'fake'}):
            with self.assertRaises(ValueError):self.client.authorize('code','verifier')

    def test_preview_is_bounded_and_uses_selected_query(self):
        with patch.object(self.client,'request',side_effect=[{'messages':[{'id':'abc'}]}, {'id':'abc','payload':{'headers':[],'body':{'data':encode(b'Interview details')}}}]) as request:
            result=self.client.preview('label:career-search newer_than:30d',limit=100)
        self.assertEqual(len(result),1)
        query=parse_qs(urlsplit(request.call_args_list[0].args[0]).query)
        self.assertEqual(query['maxResults'],['10'])
        self.assertEqual(query['q'],['label:career-search newer_than:30d'])
        self.assertEqual(result[0]['body'],'Interview details')

    def test_html_job_alert_links_survive_parsing(self):
        html='<p>A relevant job</p><a href="https://www.linkedin.com/comm/jobs/view/123456?tracking=1">View job</a><a href="https://www.indeed.com/viewjob?jk=abcdef&amp;from=email">Apply</a>'
        message=normalize_message({'id':'msg','payload':{'mimeType':'text/html','headers':[{'name':'Subject','value':'Job alert'}],'body':{'data':encode(html.encode())}}})
        links=alert_links(message)
        self.assertEqual({l['sourceUrl'] for l in links},{'https://www.linkedin.com/jobs/view/123456','https://www.indeed.com/viewjob?jk=abcdef'})
        self.assertTrue(all('verify' in l['title'] or 'review' in l['title'] for l in links))

    def test_fake_domains_are_not_trusted_as_job_boards(self):
        self.assertEqual(alert_links({'id':'x','body':'https://linkedin.com.evil.test/jobs/view/123 https://evilindeed.com/viewjob?jk=abc'}),[])

    def test_attachments_are_excluded(self):
        message=normalize_message({'id':'m','payload':{'parts':[{'mimeType':'text/plain','body':{'data':encode(b'Hello')}},{'filename':'private.txt','body':{'data':encode(b'Attachment contents')}}]}})
        self.assertEqual(message['body'],'Hello')

    def test_draft_is_created_without_sending(self):
        with patch.object(self.client,'request',return_value={'id':'draft-1'}) as request:
            result=self.client.create_draft('recruiter@example.com','Interview follow-up','Thank you for your time.')
        self.assertEqual(request.call_args.args[0],'drafts')
        raw=request.call_args.args[2]['message']['raw'];mail=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw+'='*(-len(raw)%4)))
        self.assertEqual(mail['To'],'recruiter@example.com')
        self.assertEqual(result,{'id':'draft-1','saved':True,'sent':False})

    def test_header_injection_is_rejected(self):
        for to,subject in [('recruiter@example.com\r\nBcc:x@y.com','Hi'),('recruiter@example.com','Hi\r\nBcc:x@y.com')]:
            with self.assertRaises(ValueError):self.client.create_draft(to,subject,'Body')

    def test_email_stage_hints_require_review(self):
        result=context_hints({'subject':'Example offer','body':'Discuss salary'},[{'id':'j','company':'Example'}])
        self.assertEqual(result['jobIds'],['j']);self.assertTrue(result['reviewRequired'])

class CareerTests(unittest.TestCase):
    def workspace(self):
        return {'profile':{'name':'Candidate','facts':'Unverified MBA degree','summary':'Unverified expert','confirmed':False,'entries':[
            {'id':'yes','text':'Reviewed clinical records','category':'Experience','confirmed':True,'source':'My account'},
            {'id':'no','text':'Completed MBA degree','category':'Education','confirmed':False},
            {'id':'preference','text':'Prefer remote work','category':'Preference','confirmed':True}]},
            'jobs':[{'id':'job','company':'Example','title':'Safety Nurse','requirements':[
                {'text':'Clinical review','reviewed':True,'evidenceId':'fact:yes'},
                {'text':'MBA','reviewed':True,'evidenceId':'fact:no'},
                {'text':'Location','reviewed':True,'evidenceId':'fact:preference'},
                {'text':'Unreviewed requirement','reviewed':False,'evidenceId':'fact:yes'}]}], 'stories':[], 'sessions':[]}

    def test_search_plan_encodes_real_filters_without_claiming_live_jobs(self):
        plan=search_plan({'roles':['Clinical Safety Nurse'],'location':'Cincinnati, Ohio','remote':'only'})
        item=plan['searches'][0]
        self.assertEqual(parse_qs(urlsplit(item['linkedin']).query)['f_WT'],['2'])
        self.assertEqual(parse_qs(urlsplit(item['indeed']).query)['l'],['Remote'])
        self.assertIn('not live vacancies',plan['limitations'])

    def test_tailoring_uses_only_confirmed_linked_evidence(self):
        result=tailor(self.workspace(),'job')
        self.assertIn('Reviewed clinical records',result['resume'])
        self.assertNotIn('Completed MBA degree',result['resume'])
        self.assertNotIn('Unverified expert',result['coverLetter'])
        self.assertNotIn('Prefer remote work',result['resume'])
        self.assertEqual(len(result['supported']),1)
        self.assertEqual(len(result['gaps']),2)
        self.assertIn('[Contact information]',result['resume'])

    def test_deleted_evidence_remains_a_gap(self):
        workspace=self.workspace();workspace['profile']['entries']=[]
        result=tailor(workspace,'job')
        self.assertEqual(result['supported'],[])
        self.assertEqual(len(result['gaps']),3)

if __name__=='__main__':unittest.main()
