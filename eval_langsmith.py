"""
LangSmith dataset + evaluate() workflow for the LangGraph agent
(agent_langgraph.py) -- the "eval" half of Module 9, alongside the
tracing we already get for free from LANGCHAIN_TRACING_V2.

This does NOT replace tests/test_agent.py's pytest-based eval suite --
it's a separate, smaller demonstration of LangSmith's own eval workflow
(persistent dataset + evaluate() + a dashboard you can compare future
runs against), using just 2 of the same applicants already covered by
the pytest suite (one clean, one risky) to keep API cost minimal.

The evaluator function reuses the exact same asymmetric-risk logic from
test_agent.py's test_decision_matches_or_is_more_conservative_than_label:
a false APPROVE (recommending approval for an applicant that should have
been escalated/declined) is the only hard failure, since it's the
costly direction for a real lender. It's a plain Python function, not
an LLM-as-judge call, to avoid the extra API cost that would add for no
real benefit here.

Run with: `python eval_langsmith.py` (requires the data API running and
LANGCHAIN_API_KEY set, same prerequisites as agent_langgraph.py plus
LangSmith).
"""

from langsmith import Client, evaluate

from agent_langgraph import run_investigation
from agent import extract_recommendation

DATASET_NAME = "loan-agent-eval"

# Deliberately just 2 of the 7 labeled applicants from
# tests/decision_labels.json -- one clean (cheap, few tool calls), one
# risky (more tool calls, more expensive) -- enough to demonstrate the
# LangSmith eval workflow without re-running the full label set and its
# associated API cost.
EXAMPLES = [
    {"inputs": {"applicant_id": "APPLICANT-001"}, "outputs": {"expected_recommendation": "APPROVE"}},
    {"inputs": {"applicant_id": "APPLICANT-002"}, "outputs": {"expected_recommendation": "DECLINE"}},
]


def ensure_dataset(client: Client):
    """
    Create the LangSmith dataset + examples if they don't already exist.
    Safe to call repeatedly -- checks for the dataset by name first
    rather than creating duplicates on every run.
    """
    if client.has_dataset(dataset_name=DATASET_NAME):
        return client.read_dataset(dataset_name=DATASET_NAME)

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Loan due diligence agent eval set (subset: 1 clean, 1 risky applicant).",
    )
    client.create_examples(
        inputs=[ex["inputs"] for ex in EXAMPLES],
        outputs=[ex["outputs"] for ex in EXAMPLES],
        dataset_id=dataset.id,
    )
    return dataset


def target(inputs: dict) -> dict:
    """
    The function LangSmith's evaluate() actually runs for each example.
    Takes one example's `inputs` dict (here just {"applicant_id": ...})
    and must return a dict -- evaluators below receive this as `outputs`.
    """
    result = run_investigation(inputs["applicant_id"])
    return {
        "recommendation": extract_recommendation(result["summary"]),
        "summary": result["summary"],
    }


def no_false_approve(outputs: dict, reference_outputs: dict) -> dict:
    """
    Evaluator: mirrors tests/test_agent.py's asymmetric-risk check. A
    false APPROVE -- the agent recommending approval for an applicant
    labeled ESCALATE/DECLINE -- is the only failure; being more
    conservative than the label is tolerated (efficiency loss, not a
    safety failure).

    LangSmith calls this once per example, passing the target
    function's return value as `outputs` and the example's stored
    label as `reference_outputs`. Returns a score LangSmith displays
    per-example and aggregates across the dataset.
    """
    actual = outputs["recommendation"]
    expected = reference_outputs["expected_recommendation"]
    is_false_approve = actual == "APPROVE" and expected != "APPROVE"
    return {"key": "no_false_approve", "score": 0 if is_false_approve else 1}


if __name__ == "__main__":
    client = Client()
    ensure_dataset(client)

    results = evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[no_false_approve],
        experiment_prefix="loan-agent-langgraph",
    )

    print(results)
