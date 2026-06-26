"""
Tool: get_credit_report

Fetches an applicant's credit history. Called first in every
investigation, alongside get_bank_statements, since these two are the
baseline signals strategy.md uses to decide whether to stop early or
keep investigating.
"""

from .api_client import api_get


def get_credit_report(applicant_id: str) -> dict:
    """
    Return {"credit_score": int, "late_payments": int,
    "outstanding_debt": float} for the given applicant.

    If the applicant has no credit history on file (e.g. a brand-new
    business with nothing to report), all three fields come back as
    None rather than the function raising or omitting the keys -- the
    agent needs to see "we checked, there's nothing here" as a distinct
    case from "this data point doesn't exist for any applicant."
    """
    data = api_get(f"/applicants/{applicant_id}/credit-report")
    if data is None:
        return {
            "credit_score": None,
            "late_payments": None,
            "outstanding_debt": None,
        }
    return data
