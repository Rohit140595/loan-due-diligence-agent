# TODO (Module 3/4): implement run_risk_score(evidence: dict) -> dict
#
# Combines whatever evidence the agent has gathered so far into a
# composite risk score. This tool should be purely computational —
# it does NOT decide investigation strategy (that lives in strategy.md).

from .applicant_profile import get_applicant_profile
from .bank_statements import get_bank_statements
from .credit_report import get_credit_report
from .business_filings import get_business_filings
from .industry_benchmarks import get_industry_benchmarks


def clamp(value, low, high):
    """Restrict value to the inclusive range [low, high]."""
    return max(low, min(value, high))


def run_risk_score(applicant_id: str) -> dict:
    """
    Compute a composite risk score (0-100, higher is healthier) for an
    applicant from credit, banking, filings, and industry data.

    Pulls ground-truth data itself rather than trusting it as input from
    Claude, since Claude could pass stale or fabricated numbers.
    """
    profile = get_applicant_profile(applicant_id)
    credit_report = get_credit_report(applicant_id)
    bank_statements = get_bank_statements(applicant_id)
    business_filings = get_business_filings(applicant_id)
    benchmarks = get_industry_benchmarks(profile.get("industry"))

    credit_score = credit_report["credit_score"]
    late_payments = credit_report["late_payments"]
    outstanding_debt = credit_report["outstanding_debt"]

    avg_monthly_revenue = bank_statements["avg_monthly_revenue"]
    revenue_volatility = bank_statements["revenue_volatility"]

    state_registration_status = business_filings["state_registration_status"]
    tax_filing_status = business_filings["tax_filing_status"]

    sector_default_rate = benchmarks["sector_default_rate"]

    # Credit score contributes up to 40 points, scaled linearly.
    base_score = 0
    base_score += (credit_score / 850) * 40

    # Good standing with the state and tax authority is a +/-15 swing.
    base_score += 15 if (state_registration_status == "active" and tax_filing_status == "current") else -15

    # Stable revenue is rewarded, volatile revenue is penalized, anything
    # else (e.g. "medium") is neutral.
    base_score += 15 if revenue_volatility == "low" else (-15 if revenue_volatility == "high" else 0)

    # Debt-to-annual-revenue under 20% is healthy; above that is a red flag.
    # Zero revenue isn't a "healthy ratio" -- it's its own red flag, so it
    # gets the penalty branch directly instead of dividing by zero.
    if avg_monthly_revenue == 0:
        base_score -= 15
    else:
        debt_to_revenue = outstanding_debt / (avg_monthly_revenue * 12)
        base_score += 15 if debt_to_revenue <= 0.20 else -15

    # Each late payment chips away at the score.
    base_score -= late_payments * 2

    base_score = clamp(base_score, 0, 100)

    # Applicants in high-default sectors with weak personal credit get a
    # 30% haircut on top of their base score -- the sector risk compounds
    # rather than just averaging in.
    sector_multiplier_applied = sector_default_rate >= 0.08 and credit_score < 750
    final_score = base_score * 0.7 if sector_multiplier_applied else base_score
    final_score = clamp(final_score, 0, 100)

    return {
        "risk_score": final_score,
        "base_score": base_score,
        "sector_multiplier_applied": sector_multiplier_applied,
    }
