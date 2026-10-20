import copy
import unittest
from intelligence import canonical_url, duplicate_check, rank_stories, audit_materials, source_digest
from sources import fetch_source, board_url, parse_icims, NoRedirect
from unittest.mock import patch

class IdentityTests(unittest.TestCase):
    def test_tracking_removed_but_functional_ids_preserved(self):
        a='https://EXAMPLE.com/jobs/?utm_source=email&gh_jid=12&source=careers&ref=main'
        b='http://example.com/jobs?ref=main&source=careers&gh_jid=12&utm_medium=social'
        self.assertEqual(canonical_url(a),canonical_url(b))
        self.assertNotEqual(canonical_url(a),canonical_url(a.replace('gh_jid=12','gh_jid=13')))
        self.assertIn('source=careers',canonical_url(a))

    def test_job_board_identity_and_hash_routes(self):
        self.assertEqual(canonical_url('https://www.linkedin.com/comm/jobs/view/123/?trackingId=x'),'https://www.linkedin.com/jobs/view/123')
        self.assertEqual(canonical_url('https://www.indeed.com/rc/clk?jk=abc&utm_source=mail'),'https://www.indeed.com/viewjob?jk=abc')
        self.assertNotEqual(canonical_url('https://example.com/#/job/1'),canonical_url('https://example.com/#/job/2'))

    def test_missing_or_credential_urls_never_form_identity(self):
        for value in ('N/A','','TBD','javascript:alert(1)','https://secret@example.com/job','https://example.com../job'):
            self.assertEqual(canonical_url(value),'')

    def test_exact_duplicates_and_similar_roles_are_distinct(self):
        existing=[{'id':'j','company':'Example','title':'Clinical Safety Nurse','sourceUrl':'https://example.com/job/1','posting':''}]
        self.assertEqual(duplicate_check({'sourceUrl':'https://example.com/job/1?utm_source=email'},existing)['status'],'exact')
        candidate={'company':'Example','title':'Clinical Safety Nurse','sourceUrl':'https://example.com/job/2','posting':''}
        self.assertEqual(duplicate_check(candidate,existing)['status'],'possible')
        self.assertEqual(len(existing),1)

class AuditTests(unittest.TestCase):
    def workspace(self):
        return {'profile':{'entries':[{'id':'f','text':'Registered nurse with 11 years of experience','category':'Experience','confirmed':True},
            {'id':'mba','text':'MBA coursework, degree not completed','category':'Education','confirmed':True},
            {'id':'salary','text':'Target $80,000','category':'Preference','confirmed':True}]},
            'jobs':[],'stories':[{'id':'s','title':'Review','tags':'safety','situation':'A concern','action':'Reviewed clinical information','outcome':'Prevented 25% of errors','confirmed':False}]}

    def test_unverified_figures_credentials_and_placeholders_flagged(self):
        w=self.workspace();job={'id':'j','title':'Nurse','company':'Example','requirements':[]}
        result=audit_materials(w,job,'RN with 11 years of experience. Completed MBA. Reduced errors by 25%. Target $80,000. [Contact info]')
        issues={x['detail'] for x in result['issues']}
        self.assertIn('MBA',issues);self.assertIn('25%',issues);self.assertIn('$80000',issues);self.assertIn('[Contact info]',issues)
        self.assertNotIn('11years',issues);self.assertNotIn('RN',issues)

    def test_reviewed_story_can_support_metrics(self):
        w=self.workspace();w['stories'][0]['confirmed']=True
        result=audit_materials(w,{},'Prevented 25% of errors.')
        self.assertEqual(result['issues'],[])

    def test_draft_is_flagged_when_sources_change(self):
        w=self.workspace();job={'id':'j','posting':'Original','requirements':[]};digest=source_digest(w,job)
        job['posting']='Updated requirement'
        result=audit_materials(w,job,'',digest)
        self.assertTrue(result['sourceChanged'])

    def test_story_suggestions_explain_matching_words(self):
        stories=[{'id':'a','title':'Safety review','tags':'clinical review','action':'Reviewed details','outcome':'Clarified concern','confirmed':True},
                 {'id':'b','title':'Scheduling','tags':'planning','action':'Organized shifts','outcome':'Met needs','confirmed':True}]
        result=rank_stories(stories,'How do you review clinical safety information?')
        self.assertEqual(result[0]['id'],'a');self.assertIn('review',result[0]['matchedTerms']);self.assertNotIn('weight',result[0])

class ProviderTests(unittest.TestCase):
    def test_provider_urls_cannot_point_at_arbitrary_hosts(self):
        for provider,url in [('workday','https://localhost/External'),('icims','https://icims.com.evil.test'),('workday','https://company.wd5.myworkdayjobs.com:444/External'),('icims','http://careers-example.icims.com')]:
            with self.assertRaises(ValueError):board_url(provider,url)
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://localhost'))

    def test_workday_search_and_pagination_report_partial_coverage(self):
        jobs=[{'title':'Clinical Nurse','externalPath':'/job/US/Nurse_R'+str(i),'locationsText':'Remote'} for i in range(20)]
        with patch('sources.request_json',return_value={'jobPostings':jobs,'total':200}) as remote:
            result=fetch_source('workday','https://example.wd5.myworkdayjobs.com/en-US/External','nurse')
        self.assertEqual(remote.call_count,3)
        self.assertTrue(result['meta']['partial'])
        self.assertEqual(remote.call_args.args[1]['searchText'],'nurse')
        self.assertTrue(all(j['descriptionStatus']=='summary' for j in result['jobs']))

    def test_ashby_normalizes_complete_descriptions(self):
        data={'jobs':[{'id':'a','title':'Safety Nurse','location':'Remote','descriptionPlain':'Review clinical safety','jobUrl':'https://jobs.ashbyhq.com/example/a','isListed':True}]}
        with patch('sources.request_json',return_value=data):result=fetch_source('ashby','example','safety')
        self.assertEqual(result['jobs'][0]['provider'],'ashby');self.assertFalse(result['meta']['partial'])

    def test_smartrecruiters_marks_summaries_and_scan_caps(self):
        data={'content':[{'id':'a','name':'Clinical Nurse','company':{'name':'Example'},'location':{'city':'Cincinnati'}}],'totalFound':1}
        with patch('sources.request_json',return_value=data):result=fetch_source('smartrecruiters','Example')
        self.assertEqual(result['jobs'][0]['descriptionStatus'],'summary');self.assertTrue(result['meta']['warnings'])

    def test_icims_parser_preserves_only_same_origin_jobs(self):
        html='''<li class="iCIMS_JobCardItem"><a href="/jobs/123/safety-nurse/job"><h3>Safety Nurse</h3></a><span>Location</span><span>Cincinnati</span></li><li class="iCIMS_JobCardItem"><a href="https://evil.test/jobs/124/nurse/job"><h3>Nurse</h3></a></li>'''
        result=parse_icims(html,'https://careers-example.icims.com','example')
        self.assertEqual(len(result),1);self.assertEqual(result[0]['location'],'Cincinnati')

    def test_blocked_or_changed_icims_markup_is_not_an_empty_feed(self):
        with patch('sources.request_text',return_value='<h1>Access denied</h1>'):
            with self.assertRaises(ValueError):fetch_source('icims','https://careers-example.icims.com')

if __name__=='__main__':unittest.main()
