"""
Tool: get_bank_statements

Fetches summarized bank statement data for an applicant. Called first
in every investigation, alongside get_credit_report, as the baseline
signal strategy.md uses to decide whether to stop early or keep
investigating.
"""

from .api_client import api_get


def get_bank_statements(applicant_id: str) -> dict:
    """
    Return {"avg_monthly_revenue": float, "revenue_volatility": str
    ("low"/"moderate"/"high"), "months_of_history": int} for the given
    applicant.

    If no bank statements are on file, all three fields come back as
    None rather than the function raising.
    """
    data = api_get(f"/applicants/{applicant_id}/bank-statements")
    if data is None:
        return {
            "avg_monthly_revenue": None,
            "revenue_volatility": None,
            "months_of_history": None,
        }
    return data
