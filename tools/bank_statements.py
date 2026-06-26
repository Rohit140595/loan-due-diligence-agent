from .api_client import api_get


def get_bank_statements(applicant_id: str) -> dict:
    data = api_get(f"/applicants/{applicant_id}/bank-statements")
    if data is None:
        return {
            "avg_monthly_revenue": None,
            "revenue_volatility": None,
            "months_of_history": None,
        }
    return data
