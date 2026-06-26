"""
Tool: get_applicant_profile

Fetches an applicant's basic identifying info (company name, industry).
Often the first tool called in an investigation, since the industry
value is required by get_industry_benchmarks and no other tool exposes
it.
"""

from .api_client import api_get


def get_applicant_profile(applicant_id: str) -> dict:
    """
    Return {"company_name": str, "industry": str} for the given
    applicant, or {"error": str} if no applicant with that ID exists.
    """
    data = api_get(f"/applicants/{applicant_id}/profile")
    if data is None:
        return {"error": f"No applicant found with id {applicant_id}"}
    return data
