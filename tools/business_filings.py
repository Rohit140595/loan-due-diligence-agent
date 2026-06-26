# Filing status for a small business -- state registration / tax filing
# status, NOT SEC filings (SEC applies to public companies, not relevant
# to small business loan applicants).

from .api_client import api_get


def get_business_filings(applicant_id: str) -> dict:
    data = api_get(f"/applicants/{applicant_id}/business-filings")
    if data is None:
        return {
            "state_registration_status": None,
            "tax_filing_status": None,
            "years_filed_consecutively": None,
        }
    return data
