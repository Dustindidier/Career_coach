import unittest
from domain import valid_application_deadline, validate_workspace


def deadline(status='anticipated', date='2026-10-30'):
    return dict(status=status,date=date,sourceUrl='https://example.org/job',checkedAt='2026-10-26T10:00:00Z',note='Employer anticipates window closing; exact time unspecified.',timeZone='Not published')


class DeadlineTests(unittest.TestCase):
    def test_real_dates_and_evidence_required(self):
        self.assertTrue(valid_application_deadline(deadline()))
        for changes in ({'date':'2026-02-30'},{'date':'20261030'},{'date':''},{'sourceUrl':''},{'sourceUrl':'javascript:alert(1)'},{'checkedAt':''},{'status':'confirmed'},{'note':[]}):
            self.assertFalse(valid_application_deadline({**deadline(),**changes}),changes)
        self.assertTrue(valid_application_deadline(deadline('published','2024-02-29')))

    def test_unknown_is_not_an_invented_date(self):
        for status in ('rolling','not_published','unverified'):
            self.assertTrue(valid_application_deadline(deadline(status,'')))
            self.assertFalse(valid_application_deadline(deadline(status)))

    def test_backward_compatibility_and_both_record_types(self):
        w=dict(profile=dict(name='Candidate',summary='',facts='',confirmed=False),jobs=[dict(id='j',company='Example',title='Role',stage='Exploring',posting='',notes='')],stories=[],sessions=[])
        self.assertTrue(validate_workspace(w))
        w['jobs'][0]['applicationDeadline']=deadline()
        self.assertTrue(validate_workspace(w))
        w['profile']['discovery']=[dict(id='d',company='Other',title='Role',sourceUrl='https://example.org/2',posting='',fitReasons=[],concerns=[],applicationDeadline=deadline())]
        self.assertTrue(validate_workspace(w))
        w['profile']['discovery'][0]['applicationDeadline']['date']='2026-13-01'
        self.assertFalse(validate_workspace(w))
