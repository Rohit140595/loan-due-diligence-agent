# TODO (Module 6): eval cases for agent behavior.
#
# At minimum, cover:
#   - Applicant A (clean): assert agent stops early (few tool calls)
#   - Applicant B (mixed/risky): assert agent investigates further
#   - Hallucination check: assert agent's summary only cites facts that
#     actually appear in tool results (no invented numbers/claims)

import json
from pathlib import Path

import pytest

from agent import run_investigation, extract_recommendation
from llm_judge import judge_grounding

LABELS_PATH = Path(__file__).parent / "decision_labels.json"
with open(LABELS_PATH) as f:
    DECISION_LABELS = json.load(f)


def test_clean_applicant_stops_with_minimal_investigation():
    # APPLICANT-001 is a clean profile (good credit, active filings, low
    # revenue volatility, no red flags) -- per strategy.md, the agent
    # should stop after minimal investigation rather than pulling every
    # tool. 3 calls covers profile + credit + one corroborating check.
    result = run_investigation("APPLICANT-001")

    assert len(result["tool_calls"]) <= 4, (
        f"expected minimal investigation (<=4 tool calls), got "
        f"{len(result['tool_calls'])}: "
        f"{[call['tool'] for call in result['tool_calls']]}"
    )
    

def test_risky_applicant_investigates_thoroughly():
    # APPLICANT-002 is a mixed/risky profile (weak credit, delinquent tax
    # filing, high revenue volatility, a customer-complaint lawsuit) --
    # per strategy.md, mixed or concerning signals should prompt the agent
    # to keep investigating rather than stopping early. 5 calls means it
    # went past the early "looks fine" checks into deeper verification.
    result = run_investigation("APPLICANT-002")

    assert len(result["tool_calls"]) >= 5, (
        f"expected maximum investigation (>= 5 tool calls), got "
        f"{len(result['tool_calls'])}: "
        f"{[call['tool'] for call in result['tool_calls']]}"
    )


def _assert_summary_is_grounded(applicant_id):
    """
    Every factual claim in the summary should be supported by the tool
    evidence, per an independent LLM-as-judge call (handles derived math
    and context correctly, unlike a regex-only check).
    """
    result = run_investigation(applicant_id)

    verdict = judge_grounding(result["tool_calls"], result["summary"])

    assert verdict["grounded"], (
        f"judge flagged unsupported claims: {verdict['unsupported_claims']}"
    )


def test_clean_applicant_summary_is_grounded():
    _assert_summary_is_grounded("APPLICANT-001")


def test_risky_applicant_summary_is_grounded():
    _assert_summary_is_grounded("APPLICANT-002")


# Category 3: decision quality, against human-labeled ground truth
# (tests/decision_labels.json). A false APPROVE -- recommending approval
# for an applicant that should have been escalated or declined -- is the
# dangerous failure direction, since it's the one that costs the lender
# real money. Being MORE conservative than the label (e.g. label says
# APPROVE, agent says ESCALATE) is an efficiency loss, not a safety
# failure, so it's tolerated rather than treated as a hard failure here.
#
# APPLICANT-006 is a known, accepted limitation, not a bug: strategy.md
# requires get_business_filings as a mandatory check before APPROVE
# (compliance issues are common/high-impact enough to justify the extra
# call on every applicant), but deliberately does NOT make search_news
# mandatory the same way -- the cost of checking news on every clean
# applicant wasn't judged worth catching this rarer failure mode. Adding
# every blind spot as a new mandatory check would converge on "call all
# 7 tools always," defeating the entire adaptive-depth cost savings this
# agent exists for (see Module 1/5). xfail documents this as a deliberate
# tradeoff rather than silently hiding or chasing it.
_KNOWN_LIMITATIONS = {
    "APPLICANT-006": "search_news is not a mandatory pre-APPROVE check; "
    "this applicant's only red flag is in news, a deliberate, documented "
    "cost/coverage tradeoff, not a bug to fix.",
}


@pytest.mark.parametrize(
    "applicant_id",
    [
        pytest.param(
            aid,
            marks=pytest.mark.xfail(reason=_KNOWN_LIMITATIONS[aid], strict=True),
        )
        if aid in _KNOWN_LIMITATIONS
        else aid
        for aid in sorted(DECISION_LABELS.keys())
    ],
)
def test_decision_matches_or_is_more_conservative_than_label(applicant_id):
    expected = DECISION_LABELS[applicant_id]["expected_recommendation"]
    result = run_investigation(applicant_id)
    actual = extract_recommendation(result["summary"])

    assert actual != "UNKNOWN", (
        f"{applicant_id}: could not parse a FINAL_RECOMMENDATION line from "
        f"the summary -- formatting regression"
    )

    is_false_approve = actual == "APPROVE" and expected != "APPROVE"

    assert not is_false_approve, (
        f"{applicant_id}: agent said APPROVE but expected {expected} "
        f"({DECISION_LABELS[applicant_id]['rationale']})"
    )
