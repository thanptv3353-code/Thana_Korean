import copy
import unittest
from firebase_reconciliation import reconcile_transfer

class FirebaseReconciliationTests(unittest.TestCase):
    def payload(self):
        return dict(project='korean-lao-exam',collections={
            'thana_users':[dict(id='uid_with_underscore',data=dict(username='Learner',role='student',approved=True,paid=False,epsPaid=True,seasonalPaid=False))],
            'thana_progress':[dict(id='uid_with_underscore_lesson-1',data=dict(uid='uid_with_underscore',lessonId='lesson-1',score=8,total=10,passed=True)),dict(id='unrelated',data=dict(uid='missing',words={'word':2}))]})
    def test_preserves_uid_raw_progress_and_separate_access_scopes_without_activation(self):
        payload=self.payload();original=copy.deepcopy(payload);plan=reconcile_transfer(payload)
        self.assertEqual(payload,original)
        identity=plan['identities'][0]
        self.assertEqual(identity['firebase_uid'],'uid_with_underscore')
        self.assertEqual(identity['scopes'],dict(general='unpaid',eps='paid',seasonal='unpaid'))
        self.assertEqual(identity['activation'],'blocked_pending_verified_firebase_auth')
        self.assertEqual(plan['progress'][0]['source'],payload['collections']['thana_progress'][0]['data'])
        self.assertEqual(plan['progress'][0]['issues'],[])
        self.assertEqual(plan['progress'][1]['issues'],['unknown_owner'])
        self.assertEqual(plan['summary']['applied_entitlements'],0)
    def test_ambiguous_flags_duplicates_and_malformed_scores_require_review(self):
        payload=self.payload();other=copy.deepcopy(payload['collections']['thana_users'][0]);other['id']='other';other['data'].update(username=' learner ',paid='true',epsPaid=1,approved='true',role='owner',deletedAt='timestamp')
        payload['collections']['thana_users'].append(other)
        payload['collections']['thana_progress'][0]['data'].update(score=True,total=0,passed=1)
        plan=reconcile_transfer(payload)
        self.assertIn('username_collision',plan['identities'][0]['issues'])
        self.assertEqual(plan['identities'][1]['scopes']['eps'],'unresolved')
        self.assertIn('ambiguous_paid',plan['identities'][1]['issues'])
        self.assertIn('invalid_score',plan['progress'][0]['issues'])
        self.assertIn('ambiguous_passed',plan['progress'][0]['issues'])
        self.assertEqual(plan['summary']['activated_accounts'],0)

    def test_absent_paid_fields_follow_original_unpaid_default_not_invented_membership(self):
        payload=self.payload();profile=payload['collections']['thana_users'][0]['data']
        del profile['paid'];del profile['seasonalPaid']
        identity=reconcile_transfer(payload)['identities'][0]
        self.assertEqual(identity['scopes'],dict(general='unpaid',eps='paid',seasonal='unpaid'))
        self.assertEqual(identity['absent_paid_fields'],['paid','seasonalPaid'])
        self.assertEqual(identity['issues'],[])
