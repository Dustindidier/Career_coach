import unittest
from domain import validate_workspace
from feedback import research_context


def workspace():
    return dict(profile=dict(name='Candidate',summary='',facts='',confirmed=False),jobs=[dict(id='j',title='Role',company='Example',stage='Applied',posting='',notes='')],stories=[],sessions=[])


class MatchingPreferenceTests(unittest.TestCase):
    def test_legacy_data_and_valid_user_ratings(self):
        w=workspace();self.assertTrue(validate_workspace(w))
        w['profile']['matchPreferences']=dict(weights=dict(pay=5,advancement=5,interest=3,background=4,practical=3))
        w['jobs'][0]['interestRating']=dict(value=75,note='Interesting work',updatedAt='2026-01-01')
        self.assertTrue(validate_workspace(w))
        context=research_context(w,4)
        self.assertEqual(context['interestRatings'][0]['interestRating']['value'],75)
        self.assertEqual(context['matchPreferences']['weights']['pay'],5)
        self.assertEqual(w['jobs'][0]['stage'],'Applied')

    def test_invalid_priorities_or_ratings_do_not_validate(self):
        for bad in ({},dict(pay=0,advancement=0,interest=0,background=0,practical=0),dict(pay=6,advancement=1,interest=1,background=1,practical=1),dict(pay=True,advancement=1,interest=1,background=1,practical=1)):
            w=workspace();w['profile']['matchPreferences']=dict(weights=bad)
            self.assertFalse(validate_workspace(w))
        for bad in (99,True,'75',-1):
            w=workspace();w['jobs'][0]['interestRating']=dict(value=bad,note='',updatedAt='')
            self.assertFalse(validate_workspace(w))
        w=workspace();w['profile']['discovery']=[dict(id='d',title='Role',company='Other',sourceUrl='https://example.org',posting='',fitReasons=[],concerns=[],interestRating=dict(value=25,note='a'*2001,updatedAt=''))]
        self.assertFalse(validate_workspace(w))
