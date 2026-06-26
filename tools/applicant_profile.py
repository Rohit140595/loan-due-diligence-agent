from .api_client import api_get


def get_applicant_profile(applicant_id: str) -> dict:
    data = api_get(f"/applicants/{applicant_id}/profile")
    if data is None:
        return {"error": f"No applicant found with id {applicant_id}"}
    return data
