# TODO (Module 6): eval cases for agent behavior.
#
# At minimum, cover:
#   - Applicant A (clean): assert agent stops early (few tool calls)
#   - Applicant B (mixed/risky): assert agent investigates further
#   - Hallucination check: assert agent's summary only cites facts that
#     actually appear in tool results (no invented numbers/claims)

from agent import run_investigation


def test_clean_applicant_stops_with_minimal_investigation():
    # APPLICANT-001 is a clean profile (good credit, active filings, low
    # revenue volatility, no red flags) -- per strategy.md, the agent
    # should stop after minimal investigation rather than pulling every
    # tool. 3 calls covers profile + credit + one corroborating check.
    result = run_investigation("APPLICANT-001")

    assert len(result["tool_calls"]) <= 3, (
        f"expected minimal investigation (<=3 tool calls), got "
        f"{len(result['tool_calls'])}: "
        f"{[call['tool'] for call in result['tool_calls']]}"
    )
