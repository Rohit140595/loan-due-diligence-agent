# Filing status for a small business -- state registration / tax filing
# status, NOT SEC filings (SEC applies to public companies, not relevant
# to small business loan applicants).

import json
from pathlib import Path

FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "applicants.json"


def get_business_filings(applicant_id: str) -> dict:
    with open(FIXTURES_PATH) as f:
        applicants = json.load(f)

    applicant = applicants.get(applicant_id)
    if applicant is None:
        return {"error": f"No applicant found with id {applicant_id}"}

    return applicant.get("business_filings", {
        "state_registration_status": None,
        "tax_filing_status": None,
        "years_filed_consecutively": None,
    })
