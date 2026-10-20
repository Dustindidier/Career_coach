import io
import json
import unittest
from unittest.mock import patch
from sources import fetch_jobs
from domain import guided_coach, validate_workspace

class FeedTests(unittest.TestCase):
    def test_greenhouse_normalizes_and_filters_without_scraping(self):
        data={'jobs':[{'id':1,'title':'Clinical nurse','content':'<p>Review clinical safety</p>','location':{'name':'Cincinnati'},'absolute_url':'https://example.com/jobs/1'}, {'id':2,'title':'Engineer','content':'Build software','location':{'name':'Boston'}}]}
        with patch('sources.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(data).encode())) as remote:
            result=fetch_jobs('greenhouse','example','clinical Cincinnati')
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['posting'],'Review clinical safety')
            self.assertEqual(remote.call_args.args[0].full_url,'https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true')

    def test_lever_normalizes_feed(self):
        data=[{'id':'abc','text':'Safety specialist','descriptionPlain':'Review reports','categories':{'location':'Remote'},'hostedUrl':'https://jobs.lever.co/example/abc'}]
        with patch('sources.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(data).encode())):
            result=fetch_jobs('lever','example')
            self.assertEqual(result[0]['id'],'lever:example:abc')
            self.assertEqual(result[0]['location'],'Remote')

    def test_arbitrary_network_destinations_are_rejected(self):
        with patch('sources.urllib.request.urlopen') as remote:
            for provider,board in [('manual','https://localhost'),('lever','../private'),('greenhouse','x?redirect=http://localhost')]:
                with self.assertRaises(ValueError):fetch_jobs(provider,board)
            remote.assert_not_called()

class CoachTests(unittest.TestCase):
    def test_only_reviewed_requirements_are_used(self):
        result=guided_coach({'mode':'recruiter','turn':1,'job':{'requirements':[{'text':'Unreviewed requirement','reviewed':False},{'text':'Confirmed posting passage','reviewed':True}]},'answer':'An answer'})
        self.assertIn('Confirmed posting passage',result['question'])
        self.assertNotIn('Unreviewed requirement',result['question'])

    def test_behavioral_followup_requests_concrete_evidence(self):
        result=guided_coach({'mode':'behavioral','turn':2,'answer':'I helped the team.'})
        self.assertIn('one action',result['question'])
        self.assertEqual(result['engine'],'guided')

if __name__=='__main__':unittest.main()
