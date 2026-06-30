"""
Streamlit UI for the loan due diligence agent.

Lets a human analyst pick an applicant, run the agent's investigation,
and review the result: basic applicant info, the full written report,
the parsed final recommendation, and a transparent audit trail of every
tool call the agent made along the way -- the same evidence chain used
in tests/test_agent.py's grounding checks, surfaced for a human reader
instead of an eval.

Offers a choice between two interchangeable implementations of the same
agent -- agent.py (raw Anthropic SDK) and agent_langgraph.py (LangGraph
port) -- since both expose the identical run_investigation(applicant_id)
contract (see README "Raw SDK vs. LangGraph"). Picking LangGraph also
traces the run to LangSmith automatically if LANGCHAIN_TRACING_V2=true
is set in .env.

This calls run_investigation() directly (in-process), so it needs the
same things agent.py needs to run standalone: the data API running
(`uvicorn api:app --reload`), both local databases built (see README),
and ANTHROPIC_API_KEY set in .env.

Run with: `streamlit run ui.py`
"""

import json
from pathlib import Path

import streamlit as st

from agent import extract_recommendation
from agent import run_investigation as run_investigation_raw
from agent_langgraph import run_investigation as run_investigation_langgraph

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "applicants.json"

# Both implementations share the exact same {"summary": ..., "tool_calls":
# [...]} contract, so the UI only needs to pick which function to call --
# nothing downstream of this dict needs to know or care which one ran.
_IMPLEMENTATIONS = {
    "Raw SDK (agent.py)": run_investigation_raw,
    "LangGraph (agent_langgraph.py)": run_investigation_langgraph,
}

# Badge color per recommendation -- gives the analyst an at-a-glance
# read before they dig into the written report.
_RECOMMENDATION_STYLE = {
    "APPROVE": ("✅", "green"),
    "ESCALATE": ("⚠️", "orange"),
    "DECLINE": ("⛔", "red"),
    "UNKNOWN": ("❓", "gray"),
}


def load_applicant_choices() -> dict:
    """
    Return {applicant_id: company_name} for every applicant in the local
    fixture file, used to populate the dropdown. Reads fixtures/ directly
    (not the API) since this is just for display in the picker, not part
    of the agent's actual investigation.
    """
    with open(FIXTURES_PATH) as f:
        applicants = json.load(f)
    return {aid: data["company_name"] for aid, data in applicants.items()}


def render_tool_calls(tool_calls: list):
    """Render the agent's full audit trail: every tool it called, with
    what it asked for and what it got back, in the order it called
    them."""
    st.subheader(f"Investigation trail ({len(tool_calls)} tool calls)")
    for i, call in enumerate(tool_calls, start=1):
        with st.expander(f"{i}. {call['tool']}({call['input']})"):
            st.json(call["output"])


def main():
    st.set_page_config(page_title="Loan Due Diligence Agent", layout="wide")
    st.title("Loan Due Diligence Agent")
    st.caption(
        "Agent investigates an applicant and produces a recommendation. "
        "Final approve/decline authority rests with the human analyst."
    )

    choices = load_applicant_choices()
    applicant_id = st.selectbox(
        "Select an applicant to investigate",
        options=list(choices.keys()),
        format_func=lambda aid: f"{aid} -- {choices[aid]}",
    )

    implementation_name = st.radio(
        "Agent implementation",
        options=list(_IMPLEMENTATIONS.keys()),
        horizontal=True,
        help="Both call the identical strategy.md and the same tools -- "
        "only the orchestration code differs. LangGraph runs also trace "
        "to LangSmith if LANGCHAIN_TRACING_V2 is set in .env.",
    )
    run_investigation = _IMPLEMENTATIONS[implementation_name]

    if st.button("Run investigation", type="primary"):
        with st.spinner("Investigating... this calls the Anthropic API and may take a minute."):
            result = run_investigation(applicant_id)
        # Cache in session state so the result survives Streamlit's
        # rerun-on-every-interaction model (e.g. expanding a tool call
        # below shouldn't re-run the investigation).
        st.session_state["result"] = result
        st.session_state["applicant_id"] = applicant_id

    if "result" not in st.session_state:
        st.info("Pick an applicant and click \"Run investigation\" to begin.")
        return

    result = st.session_state["result"]
    recommendation = extract_recommendation(result["summary"])
    icon, color = _RECOMMENDATION_STYLE[recommendation]

    st.markdown(
        f"### Recommendation: :{color}[{icon} {recommendation}]"
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Full report")
        st.markdown(result["summary"])
    with col2:
        render_tool_calls(result["tool_calls"])


if __name__ == "__main__":
    main()
