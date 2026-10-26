import unittest
from win_validation.evaluation.final_evaluation import evaluate_source, evaluate_account, evaluate_leave_one_out
from win_validation.evaluation.retry_policy import classify_attempt, should_retry, page_complete

class FinalEvaluationTests(unittest.TestCase):
    def test_no_evidence_never_approved_or_rejected(self):
        self.assertEqual(evaluate_source({'http_status':200})['state'],'INSUFFICIENT_EVIDENCE')
    def test_http_200_without_peru_not_approved(self):
        e={'evidence_ids':['x'],'api_reachable':True,'peru_evidence':False,'operator_attribution':False,'useful_for_role':False}
        self.assertEqual(evaluate_source(e)['state'],'INSUFFICIENT_EVIDENCE')
    def test_empty_window_not_rejected(self):
        r=evaluate_source({'evidence_ids':['x'],'api_reachable':True,'empty_valid_window':True})
        self.assertEqual(r['state'],'INSUFFICIENT_EVIDENCE'); self.assertFalse(r['reject_allowed'])
    def test_license_review_deferred_does_not_block_technical_approval(self):
        e={k:True for k in ('api_reachable','peru_evidence','operator_attribution','useful_for_role','freshness_measured','independent_incremental_value','quota_cost_verified')}
        e['evidence_ids']=['x']; e['commercial_authorized']=False
        self.assertEqual(evaluate_source(e)['state'],'APPROVED')
    def test_only_all_requirements_can_approve(self):
        e={k:True for k in ('api_reachable','peru_evidence','operator_attribution','useful_for_role','freshness_measured','independent_incremental_value','quota_cost_verified')}; e['evidence_ids']=['x']
        self.assertEqual(evaluate_source(e)['state'],'APPROVED')

    def test_institutional_account_useful_post_without_replies_not_discarded(self):
        result=evaluate_account({'evidence_ids':['x'],'official_identity_verified':True,
          'replies_observed':0,'useful_official_communication':True})
        self.assertEqual(result['state'],'CONDITIONAL')

    def test_account_technical_approval_does_not_depend_on_license_review(self):
        result=evaluate_account({'evidence_ids':['x'],'official_identity_verified':True,
          'useful_official_communication':True,'peru_evidence':True,'freshness_measured':True,
          'independent_incremental_value':True,'commercial_authorized':False,'quota_cost_verified':True})
        self.assertEqual(result['state'],'APPROVED')

    def test_shared_family_does_not_supply_independent_value(self):
        result=evaluate_source({'evidence_ids':['x'],'api_reachable':True,'peru_evidence':True,
          'useful_for_role':True,'independent_incremental_value':False})
        self.assertNotEqual(result['state'],'APPROVED')

    def test_leave_one_out_without_history_has_no_invented_loss(self):
        self.assertEqual(evaluate_leave_one_out(sufficient_history=False)['state'],'INSUFFICIENT_EVIDENCE')

    def test_retry_classes_and_stops(self):
        self.assertEqual(classify_attempt(401),'AUTH_BLOCKED')
        self.assertEqual(classify_attempt(403),'AUTH_BLOCKED')
        self.assertEqual(classify_attempt(429),'RATE_LIMITED')
        for code in (500,502,503,504): self.assertEqual(classify_attempt(code),'TRANSIENT_ERROR')
        self.assertFalse(should_retry(status='AUTH_BLOCKED',attempt=1))
        self.assertFalse(should_retry(status='EMPTY_VALID_RESPONSE',attempt=1,query_changed=False))
        self.assertTrue(should_retry(status='EMPTY_VALID_RESPONSE',attempt=1,query_changed=True))

    def test_rate_limit_respects_retry_after_and_quota(self):
        self.assertTrue(should_retry(status='RATE_LIMITED',attempt=1,retry_after_available=True))
        self.assertFalse(should_retry(status='RATE_LIMITED',attempt=1,retry_after_available=False))
        self.assertFalse(should_retry(status='TRANSIENT_ERROR',attempt=1,quota_safe=False))

    def test_pagination_and_recovery(self):
        self.assertFalse(page_complete('https://api.example/page=2'))
        self.assertTrue(page_complete(None))
        self.assertEqual(classify_attempt(200),'SUCCESS_WITH_EVIDENCE')

if __name__=='__main__': unittest.main()
