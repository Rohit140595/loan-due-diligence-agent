"""
Tool: get_industry_benchmarks

Fetches sector-level reference data (default rate, average revenue) for
one industry. Unlike the other tools, this is NOT tied to any individual
applicant -- "the bakery sector's average default rate" is the same
number regardless of which applicant you're investigating.

Requires the industry value, which is only available from
get_applicant_profile -- no other tool exposes it.
"""

from .api_client import api_get


def get_industry_benchmarks(industry: str) -> dict:
    """
    Return {"sector_default_rate": float, "sector_avg_revenue": float}
    for the given industry, or {"error": str} if the industry isn't
    recognized.
    """
    data = api_get(f"/industry-benchmarks/{industry}")
    if data is None:
        return {"error": f"No benchmark data found for industry '{industry}'"}
    return data
