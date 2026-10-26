import copy
import unittest
from applications import review_digest, preparation_packet
from intelligence import source_digest
from domain import guided_coach

class ApplicationTests(unittest.TestCase):
    def fixture(self):
        w={'profile':{'name':'Candidate','entries':[{'id':'rn','category':'Credential','text':'Registered nurse','confirmed':True,'source':'My record'}, {'id':'private','category':'Preference','text':'Private compensation minimum','confirmed':True,'source':'My preference'}]},'jobs':[],'stories':[]}
        j={'id':'j','title':'Research Nurse','company':'Example','stage':'Exploring','sourceUrl':'https://example.com/jobs/1','requirements':[], 'materials':{'resume':'Registered nurse','coverLetter':'I am interested in the opportunity.'}}
        j['materials']['sourceDigest']=source_digest(w,j)
        j['applicationWorkflow']={'reviewed':True,'screeningNotes':'Review actual website questions.','reviewedAt':'2026-10-26T12:00:00Z'}
        w['jobs']=[j];j['applicationWorkflow']['reviewDigest']=review_digest(w,j)
        return w,j

    def test_preparation_packet_does_not_authorize_submission_or_expose_preferences(self):
        w,j=self.fixture();packet=preparation_packet(w,'j')
        self.assertFalse(packet['submissionAuthorized'])
        self.assertEqual(packet['job']['sourceUrl'],j['sourceUrl'])
        self.assertNotIn('private',[e['id'] for e in packet['confirmedFacts']])
        self.assertNotIn('send',packet['allowedActions'])

    def test_existing_application_cannot_be_prepared_as_new_submission(self):
        for stage in ('Applied','Interviewing','Offer','Closed'):
            w,j=self.fixture();j['stage']=stage
            with self.assertRaisesRegex(ValueError,'already applied'):preparation_packet(w,'j')

    def test_edits_invalidate_prior_review(self):
        for kind in ('name','resume','notes','target'):
            w,j=self.fixture()
            if kind=='name':w['profile']['name']='Changed'
            if kind=='resume':j['materials']['resume']='Changed'
            if kind=='notes':j['applicationWorkflow']['screeningNotes']='Changed answer'
            if kind=='target':j['sourceUrl']='https://example.com/jobs/2'
            with self.assertRaisesRegex(ValueError,'Changes invalidate'):preparation_packet(w,'j')

    def test_unresolved_placeholders_prevent_packet_export(self):
        w,j=self.fixture();j['materials']['resume']='Registered nurse [phone]';j['applicationWorkflow']['reviewDigest']=review_digest(w,j)
        with self.assertRaisesRegex(ValueError,'claims/placeholder'):preparation_packet(w,'j')

    def test_missing_target_or_confirmed_profile_prevents_handoff(self):
        w,j=self.fixture();j['sourceUrl']=''
        with self.assertRaisesRegex(ValueError,'HTTPS'):preparation_packet(w,'j')
        w,j=self.fixture();w['profile']['entries']=[];j['applicationWorkflow']['reviewDigest']=review_digest(w,j)
        with self.assertRaisesRegex(ValueError,'confirmed career facts'):preparation_packet(w,'j')

class RolePreparationTests(unittest.TestCase):
    def role(self):
        return {'title':'Clinical Research Manager','company':'Example Oncology','requirements':[], 'preparation':{
            'status':'posting_verified','questions':{'recruiter':['Why research operations?','How would you coach the team?'], 'safety':['A trial visit has missing eligibility information. What would you do?']},
            'scenarioCheckpoint':'Follow the applicable protocol and investigator escalation process.'}}

    def test_selected_role_uses_its_own_questions(self):
        result=guided_coach({'mode':'recruiter','turn':0,'job':self.role()})
        self.assertEqual(result['question'],'Why research operations?')
        self.assertIn('reviewed role plan',result['label'])

    def test_research_scenarios_replace_pharmacovigilance_defaults(self):
        result=guided_coach({'mode':'safety','turn':0,'job':self.role()})
        self.assertIn('eligibility',result['question']);self.assertNotIn('headache',result['question'])
        feedback=guided_coach({'mode':'safety','turn':1,'job':self.role(),'answer':'I would escalate the missing information.'})
        self.assertIn('investigator',feedback['feedback'][-1]);self.assertTrue(feedback['complete'])

    def test_provisional_role_is_labeled(self):
        job=self.role();job['preparation']['status']='provisional'
        self.assertIn('verification pending',guided_coach({'mode':'recruiter','turn':0,'job':job})['label'])

if __name__=='__main__':unittest.main()
