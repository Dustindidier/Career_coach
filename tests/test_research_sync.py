import copy
import unittest
from research_sync import merge_batch
from test_career_paths import path
from test_deadlines import deadline


def workspace():
    return dict(profile=dict(name='Candidate',summary='',facts='',confirmed=False,discovery=[]),jobs=[dict(id='existing',company='Prior',title='Role',stage='Applied',posting='',notes='',materials=dict(resume='Keep',coverLetter='Keep'))],stories=[],sessions=[])


def candidate():
    return dict(company='Example',title='Clinical specialist',sourceUrl='https://example.org/jobs/1',posting='Full researched description',availabilityEvidence='Employer checked with current research brief',verifiedAt='2026-01-01',salary='Published base range',location='Cincinnati, OH',fitReasons=['Relevant clinical route'],concerns=['Confirm exact travel'],careerPath=path(),applicationDeadline=deadline())


class ResearchSyncTests(unittest.TestCase):
    def test_import_preserves_existing_jobs_and_only_creates_pending_research(self):
        w=workspace();before=copy.deepcopy(w)
        result,stats=merge_batch(w,[candidate()],'daily:one','2026-01-01')
        self.assertEqual(stats['added'],1)
        self.assertEqual(w,before)
        self.assertEqual(result['jobs'],w['jobs'])
        row=result['profile']['discovery'][0]
        self.assertEqual(row['decision'],'pending')
        self.assertEqual(row['applicationDeadline'],candidate()['applicationDeadline'])
        self.assertNotIn('materials',row)
        again,stats=merge_batch(result,[candidate()],'daily:one','2026-01-01')
        self.assertTrue(stats['duplicateRun'])
        self.assertEqual(again,result)

    def test_deduplicates_passed_roles_tracking_links_and_titles(self):
        w=workspace();r=candidate();w['profile']['discovery']=[{**r,'id':'prior','decision':'rejected'}]
        result,stats=merge_batch(w,[{**r,'sourceUrl':r['sourceUrl']+'?utm_source=alert'},{**r,'sourceUrl':'https://other.example/jobs/99'}],'daily:two','2026-01-02')
        self.assertEqual(stats['added'],0)
        self.assertEqual(stats['skipped'],2)
        self.assertEqual(result['profile']['discovery'][0]['decision'],'rejected')

    def test_rejects_entire_malformed_batch_and_records_valid_empty_run(self):
        w=workspace();before=copy.deepcopy(w)
        with self.assertRaises(ValueError):merge_batch(w,[candidate(),{**candidate(),'careerPath':None}],'bad','2026-01-01')
        self.assertEqual(w,before)
        result,stats=merge_batch(w,[],'empty','2026-01-01')
        self.assertEqual(stats['added'],0)
        self.assertEqual(result['profile']['dailyResearch']['lastStatus'],'succeeded')
        self.assertEqual(result['jobs'],w['jobs'])
