from .api_client import api_get


def get_credit_report(applicant_id: str) -> dict:
    data = api_get(f"/applicants/{applicant_id}/credit-report")
    if data is None:
        return {
            "credit_score": None,
            "late_payments": None,
            "outstanding_debt": None,
        }
    return data
