# TODO (Module 3/4): implement get_bank_statements(applicant_id) -> dict
#
# Should return simulated fields like:
#   { "avg_monthly_revenue": float, "revenue_volatility": str, "months_of_history": int }

import json
from pathlib import Path

FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "applicants.json"

def get_bank_statements(applicant_id: str) -> dict:
    with open(FIXTURES_PATH) as f:
        applicants = json.load(f)

    applicant = applicants.get(applicant_id)
    if applicant is None:
        return {"error": f"No applicant found with id {applicant_id}"}

    return applicant.get("bank_statements", {
        "avg_monthly_revenue": None,
        "revenue_volatility": None,
        "months_of_history": None,
    })