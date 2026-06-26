"""
Tool: get_business_filings

Fetches a small business's state registration and tax filing status --
NOT SEC filings (SEC applies to public companies, not relevant to small
business loan applicants).

strategy.md requires this as a mandatory check before any APPROVE
recommendation, regardless of how clean credit/revenue look: compliance
issues (e.g. delinquent taxes) are invisible in credit/bank data and can
disqualify an otherwise-clean applicant.
"""

from .api_client import api_get


def get_business_filings(applicant_id: str) -> dict:
    """
    Return {"state_registration_status": str, "tax_filing_status": str,
    "years_filed_consecutively": int} for the given applicant's
    business.

    If no filing records are on file, all three fields come back as
    None rather than the function raising.
    """
    data = api_get(f"/applicants/{applicant_id}/business-filings")
    if data is None:
        return {
            "state_registration_status": None,
            "tax_filing_status": None,
            "years_filed_consecutively": None,
        }
    return data
