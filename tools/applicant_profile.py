import json
from pathlib import Path

FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "applicants.json"


def get_applicant_profile(applicant_id: str) -> dict:
    with open(FIXTURES_PATH) as f:
        applicants = json.load(f)

    applicant = applicants.get(applicant_id)
    if applicant is None:
        return {"error": f"No applicant found with id {applicant_id}"}

    return {"company_name" : applicant.get("company_name", None)
            , "industry":  applicant.get("industry", None)
            }