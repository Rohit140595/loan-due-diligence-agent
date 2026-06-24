# TODO (Module 3/4): implement get_credit_report(applicant_id) -> dict
#
# Should return simulated but realistic fields, e.g.:
#   { "credit_score": int, "late_payments": int, "outstanding_debt": float }
#
# Tool description (for the Claude API tools list) belongs in agent.py,
# not here — this file is just the function Claude's request triggers.

import json
from pathlib import Path

FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "applicants.json"

def get_credit_report(applicant_id: str) -> dict:
    with open(FIXTURES_PATH) as f:
        applicants = json.load(f)

    applicant = applicants.get(applicant_id)
    if applicant is None:
        return {"error": f"No applicant found with id {applicant_id}"}

    return applicant.get("credit_report", {
        "credit_score": None,
        "late_payments": None,
        "outstanding_debt": None,
    })
