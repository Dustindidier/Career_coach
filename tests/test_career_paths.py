import copy
import unittest
from domain import validate_workspace, valid_career_path


def path():
    return dict(schemaVersion=1,summary='Conditional progression',bedsideFit='Office work',industryBridge='Requires trial exposure',entryFit='Confirm actual qualifications',assumptions='Current-dollar estimates, not promises',updatedAt='2026-01-01',milestones=['Own a project'],gaps=['Industry experience'],questions=['What training is provided?'],steps=[dict(timeframe='Years 1–3',role='Specialist',salary='Estimate; confirm employer band',basis='Market estimate',experience='Trial delivery',gate='Demonstrated ownership')],sources=[dict(label='Reference',url='https://example.org/reference',note='Illustrative benchmark')])


class CareerPathTests(unittest.TestCase):
    def workspace(self):
        return dict(profile=dict(name='Candidate',summary='',facts='',confirmed=False),jobs=[dict(id='j',company='Example',title='Specialist',posting='',notes='',stage='Exploring')],stories=[],sessions=[])

    def test_legacy_and_job_and_discovery_paths_validate(self):
        w=self.workspace()
        self.assertTrue(validate_workspace(w))
        w['jobs'][0]['careerPath']=path()
        w['profile']['discovery']=[dict(id='d',company='Other',title='Role',posting='',sourceUrl='https://example.org/jobs/1',fitReasons=[],concerns=[],decision='pending',careerPath=path())]
        self.assertTrue(validate_workspace(w))
        w['profile']['discovery'][0]['careerPath']['steps'][0]['salary']=90000
        self.assertFalse(validate_workspace(w))

    def test_reject_malformed_or_unbounded_paths_before_saving(self):
        self.assertTrue(valid_career_path(path()))
        for key,value in [('steps',[]),('sources',[dict(label='Unsafe',url='javascript:alert(1)',note='')]),('milestones','text'),('entryFit',None),('schemaVersion',2)]:
            p=path();p[key]=value
            self.assertFalse(valid_career_path(p),key)
        p=path();p['steps']=[p['steps'][0]]*9
        self.assertFalse(valid_career_path(p))
        w=self.workspace();w['jobs'][0]['careerPath']=None
        self.assertFalse(validate_workspace(w))

    def test_validating_does_not_change_stages_or_materials(self):
        w=self.workspace();w['jobs'][0].update(stage='Applied',materials=dict(resume='Original',coverLetter='Original'),careerPath=path())
        before=copy.deepcopy(w)
        self.assertTrue(validate_workspace(w))
        self.assertEqual(w,before)

    def test_research_context_carries_path_summary_without_materials(self):
        from feedback import research_context
        w=self.workspace();w['jobs'][0].update(careerPath=path(),materials=dict(resume='Private source text',coverLetter='Private letter'))
        context=research_context(w,8)
        self.assertEqual(context['careerPathSummaries'][0]['industryBridge'],'Requires trial exposure')
        self.assertNotIn('Private source text',str(context))
