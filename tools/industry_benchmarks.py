# Sector-level reference data -- not tied to any individual applicant.

from .api_client import api_get


def get_industry_benchmarks(industry: str) -> dict:
    data = api_get(f"/industry-benchmarks/{industry}")
    if data is None:
        return {"error": f"No benchmark data found for industry '{industry}'"}
    return data
