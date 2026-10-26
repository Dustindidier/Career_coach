import copy
import unittest

from domain import validate_workspace
from feedback import valid_feedback, research_context


def row(status='proposed'):
    return dict(id='source:1', text='Prioritize career progression and recurring pay.',
                source='User-shared conversation', sourceType='conversation', status=status,
                createdAt='2026-01-01', reviewedAt='2026-01-02' if status == 'active' else '')


class FeedbackTests(unittest.TestCase):
    def workspace(self):
        return dict(profile=dict(name='Candidate', summary='', facts='', confirmed=False), jobs=[], stories=[], sessions=[])

    def test_legacy_workspace_remains_valid_and_context_empty(self):
        w = self.workspace()
        self.assertTrue(validate_workspace(w))
        context = research_context(w, 7)
        self.assertEqual(context['revision'], 7)
        self.assertEqual(context['activeFeedback'], [])

    def test_review_required_and_malformed_ledger_rejected(self):
        r = row('active')
        self.assertTrue(valid_feedback([r]))
        r['reviewedAt'] = ''
        self.assertFalse(valid_feedback([r]))
        for change in ({'text': []}, {'status': 'confirmed'}, {'sourceType': 'system'}, {'source': ''}):
            self.assertFalse(valid_feedback([{**row(), **change}]))
        self.assertFalse(valid_feedback([row(), row()]))
        w = self.workspace(); w['profile']['researchFeedback'] = [r]
        self.assertFalse(validate_workspace(w))

    def test_context_separates_suggestions_history_and_reviewed_guidance(self):
        w = self.workspace()
        w['profile']['researchFeedback'] = [row('active'), {**row(), 'id': '2'}, {**row('superseded'), 'id': '3'}]
        w['profile']['searchPreferences'] = {'compensation': 'Confirm target'}
        w['profile']['entries'] = [dict(id='yes', text='Confirmed experience', confirmed=True, category='Experience'),
                                   dict(id='no', text='Unconfirmed degree', confirmed=False, category='Education')]
        w['profile']['referenceDocuments'] = [{'extractedText': 'Private original'}]
        before = copy.deepcopy(w)
        result = research_context(w, 11)
        self.assertEqual([r['id'] for r in result['activeFeedback']], ['source:1'])
        self.assertEqual([r['id'] for r in result['reviewQueue']], ['2'])
        self.assertEqual([r['id'] for r in result['feedbackHistory']], ['3'])
        self.assertEqual([e['id'] for e in result['confirmedFacts']], ['yes'])
        self.assertNotIn('Private original', str(result))
        self.assertEqual(w, before)

    def test_decision_reason_and_existing_applications_survive_handoff(self):
        w = self.workspace()
        w['profile']['discovery'] = [dict(id='a', company='Example', title='Role', decision='rejected',
                                                decisionReason='Pay cut is too large', decidedAt='2026-01-01'),
                                     dict(id='b', decision='pending')]
        w['jobs'] = [dict(id='j', title='Other role', company='Other', stage='Applied', communications=[{'body':'Private email'}])]
        result = research_context(w, 9)
        self.assertEqual(len(result['decisions']), 1)
        self.assertEqual(result['decisions'][0]['decisionReason'], 'Pay cut is too large')
        self.assertEqual(result['trackedRoles'][0]['stage'], 'Applied')
        self.assertNotIn('Private email', str(result))
