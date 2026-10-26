from __future__ import annotations

STATES={'APPROVED','REJECTED','CONDITIONAL','INSUFFICIENT_EVIDENCE'}

def evaluate_source(evidence: dict) -> dict:
    """Rules-only evaluator. Missing/empty observations cannot become a rejection."""
    required=('api_reachable','peru_evidence','operator_attribution','useful_for_role','freshness_measured','independent_incremental_value','quota_cost_verified')
    if not evidence.get('evidence_ids') or evidence.get('api_reachable') is False:
        state='INSUFFICIENT_EVIDENCE'
    elif all(evidence.get(k) is True for k in required):
        state='APPROVED'
    elif evidence.get('useful_for_role') is True and evidence.get('peru_evidence') is True:
        state='CONDITIONAL'
    else:
        state='INSUFFICIENT_EVIDENCE'
    return {'state':state,'passed_criteria':[k for k in required if evidence.get(k) is True],
            'failed_or_unknown_criteria':[k for k in required if evidence.get(k) is not True],
            'reject_allowed':False if state=='INSUFFICIENT_EVIDENCE' else None}

def evaluate_account(evidence: dict) -> dict:
    """Reversible account decision; zero replies cannot erase useful official posts."""
    if not evidence.get('evidence_ids') or evidence.get('official_identity_verified') is not True:
        state='INSUFFICIENT_EVIDENCE'
    elif evidence.get('useful_official_communication') is True:
        required=('peru_evidence','freshness_measured','independent_incremental_value','quota_cost_verified')
        state='APPROVED' if all(evidence.get(key) is True for key in required) else 'CONDITIONAL'
    else:
        state='INSUFFICIENT_EVIDENCE'
    return {'state':state,'reject_allowed':False if state=='INSUFFICIENT_EVIDENCE' else None}

def evaluate_leave_one_out(*, sufficient_history: bool, before: dict | None=None, after: dict | None=None) -> dict:
    if not sufficient_history or before is None or after is None:
        return {'state':'INSUFFICIENT_EVIDENCE','delta':None}
    keys=set(before) & set(after)
    delta={key: before[key]-after[key] for key in keys
           if isinstance(before[key],(int,float)) and isinstance(after[key],(int,float))}
    return {'state':'MEASURED','delta':delta}
