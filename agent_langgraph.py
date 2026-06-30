"""
LangGraph + LangChain port of agent.py, built as a separate file so the
raw hand-written loop in agent.py keeps working untouched and the two
can be diffed/compared directly.

Mechanically this is the same agent as agent.py: same tools, same
strategy.md system prompt, same stop/continue logic -- only the
orchestration code changed. The while-loop that called Claude, checked
stop_reason, and dispatched tool calls by hand is replaced by:

  - a 2-node graph ("agent" calls Claude, "tools" executes whatever it
    requested)
  - a conditional edge (tools_condition) that inspects the last
    message for tool calls, the same signal agent.py's
    `response.stop_reason == "tool_use"` check used
  - an edge from "tools" back to "agent", which is the loop itself,
    now expressed as graph structure instead of a Python `while True`

Each @tool-wrapped function below is a thin wrapper around the
corresponding function in tools/*.py -- the underlying tools are not
duplicated or modified, just exposed in LangChain's tool format. The
docstring on each wrapper is what LangChain's @tool decorator reads to
build the tool's schema/description for Claude (along with the
parameter's type hint) -- no hand-written JSON schema needed, unlike
the TOOLS list in agent.py.
"""

import ast

from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

# Reused as-is, not reimplemented: this is pure text parsing on the
# final summary string, with no dependency on which agent produced it
# -- both versions end their summary in the same
# "FINAL_RECOMMENDATION: ..." line, since strategy.md is identical.
from agent import extract_recommendation

from tools import get_applicant_profile as _get_applicant_profile
from tools import get_bank_statements as _get_bank_statements
from tools import get_credit_report as _get_credit_report
from tools import get_business_filings as _get_business_filings
from tools import get_industry_benchmarks as _get_industry_benchmarks
from tools import search_news as _search_news
from tools import run_risk_score as _run_risk_score


@tool
def get_applicant_profile(applicant_id: str) -> dict:
    """
    Return {"company_name": str, "industry": str} for the given
    applicant, or {"error": str} if no applicant with that ID exists.
    """
    return _get_applicant_profile(applicant_id)


@tool
def get_bank_statements(applicant_id: str) -> dict:
    """
    Return {"avg_monthly_revenue": float, "revenue_volatility": str
    ("low"/"moderate"/"high"), "months_of_history": int} for the given
    applicant.

    If no bank statements are on file, all three fields come back as
    None rather than the function raising.
    """
    return _get_bank_statements(applicant_id)


@tool
def get_credit_report(applicant_id: str) -> dict:
    """
    Return {"credit_score": int, "late_payments": int,
    "outstanding_debt": float} for the given applicant.

    If the applicant has no credit history on file (e.g. a brand-new
    business with nothing to report), all three fields come back as
    None rather than the function raising or omitting the keys -- the
    agent needs to see "we checked, there's nothing here" as a distinct
    case from "this data point doesn't exist for any applicant."
    """
    return _get_credit_report(applicant_id)


@tool
def get_business_filings(applicant_id: str) -> dict:
    """
    Return {"state_registration_status": str, "tax_filing_status": str,
    "years_filed_consecutively": int} for the given applicant's
    business.

    If no filing records are on file, all three fields come back as
    None rather than the function raising.
    """
    return _get_business_filings(applicant_id)


@tool
def get_industry_benchmarks(industry: str) -> dict:
    """
    Return {"sector_default_rate": float, "sector_avg_revenue": float}
    for the given industry, or {"error": str} if the industry isn't
    recognized.
    """
    return _get_industry_benchmarks(industry)


@tool
def search_news(applicant_id: str) -> list:
    """
    Return up to 3 news articles relevant to the given applicant's
    company, as a list of {"headline": str, "snippet": str} dicts (or
    an empty list if nothing relevant was indexed for this applicant).

    Looks up the company name via get_applicant_profile, then queries
    Chroma with a generic risk-oriented query string, scoped to this
    applicant only via metadata filtering (`where={"applicant_id": ...}`)
    -- this keeps the lookup applicant-specific while still ranking
    results by semantic relevance rather than a literal text match.
    """
    return _search_news(applicant_id)


@tool
def run_risk_score(applicant_id: str) -> dict:
    """
    Compute a composite risk score (0-100, higher is healthier) for an
    applicant from credit, banking, filings, and industry data.

    Pulls ground-truth data itself rather than trusting it as input from
    Claude, since Claude could pass stale or fabricated numbers.
    """
    return _run_risk_score(applicant_id)

# Every tool the agent can call -- same set as TOOL_FUNCTIONS in
# agent.py, just in LangChain's @tool-wrapped form instead of a plain
# dict of name -> function.
TOOLS = [get_applicant_profile, get_credit_report, get_bank_statements,
         get_business_filings, get_industry_benchmarks, search_news, run_risk_score]

# Same system prompt file as agent.py -- strategy.md doesn't change for
# the port, since it's just text passed to the model either way. The
# framework changes orchestration code, not the agent's behavior.
with open("strategy.md") as f:
    STRATEGY = f.read()

# bind_tools() is the LangChain equivalent of passing `tools=TOOLS` to
# client.messages.create() in agent.py -- it tells the model which
# tools are available and lets it request them in its responses.
llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0).bind_tools(TOOLS)


def call_model(state: MessagesState):
    """
    The "agent" node: call Claude with the system prompt + full message
    history so far, and append its response to the conversation.

    Equivalent to one iteration's `response = call_claude(messages)` in
    agent.py's loop -- the SystemMessage is prepended fresh on every
    call (the API is still stateless underneath LangChain) rather than
    using a provider-specific system kwarg, so this function would work
    unchanged if `llm` were swapped for a different provider's chat
    model.
    """
    messages = [SystemMessage(content=STRATEGY)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


# The graph itself: two nodes ("agent" calls Claude, "tools" executes
# whatever Claude requested) wired together to reproduce agent.py's
# while-loop as graph structure instead of explicit Python control flow.
#
#   START -> agent -> [tools_condition] -> tools -> agent -> ... -> END
#
# tools_condition is a prebuilt LangGraph function that inspects the
# last message for tool calls -- the same signal agent.py's
# `response.stop_reason == "tool_use"` check used -- and routes to the
# "tools" node if there are any, or to END (the graph's stop condition)
# if not. ToolNode is the prebuilt equivalent of agent.py's manual
# `for block in response.content: ... func(**block.input)` loop: given
# the list of available tools, it executes whichever ones the last
# message requested and returns their results as messages.
graph = StateGraph(MessagesState)
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(TOOLS))
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "agent")

# Compiling turns the graph definition into something runnable, e.g.
# app.invoke({"messages": [HumanMessage(content="...")]})
app = graph.compile()


def run_investigation(applicant_id: str) -> dict:
    """
    LangGraph equivalent of agent.py's run_investigation(). Drives the
    compiled graph to completion (LangGraph handles the looping
    internally -- there's no explicit while-loop here, unlike
    agent.py) and reshapes the result into the exact same
    {"summary": str, "tool_calls": [{"tool", "input", "output"}, ...]}
    shape agent.py returns, so downstream code -- extract_recommendation,
    even the existing eval suite -- can be reused unchanged against
    either version.
    """
    initial_state = {
        "messages": [HumanMessage(content=f"Investigate loan applicant: {applicant_id}")]
    }
    final_state = app.invoke(initial_state)
    messages = final_state["messages"]

    # LangGraph doesn't hand you a separate tool-call log the way
    # agent.py's hand-written loop builds tool_call_log as it goes --
    # it just leaves everything in the message history. Reconstruct an
    # equivalent log here: every AIMessage's tool_calls, paired with the
    # ToolMessage that answered each one (matched by tool_call_id).
    tool_results_by_id = {
        m.tool_call_id: m.content for m in messages if isinstance(m, ToolMessage)
    }

    tool_calls = []
    for m in messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            for call in m.tool_calls:
                raw_output = tool_results_by_id.get(call["id"])
                try:
                    # ToolNode stringifies non-string tool results (our
                    # tools return dicts/lists) via Python's str(), not
                    # JSON -- ast.literal_eval recovers the original
                    # Python object so callers see the same shape
                    # agent.py's tool_calls log provides. Falls back to
                    # the raw string if that fails for any reason.
                    output = ast.literal_eval(raw_output)
                except (ValueError, SyntaxError, TypeError):
                    output = raw_output
                tool_calls.append(
                    {"tool": call["name"], "input": call["args"], "output": output}
                )

    # The final AIMessage (the one with no tool_calls, which is what
    # made tools_condition route to END) holds the written summary,
    # ending in the same "FINAL_RECOMMENDATION: ..." line strategy.md
    # requires in both versions.
    summary = messages[-1].content

    return {"summary": summary, "tool_calls": tool_calls}


if __name__ == "__main__":
    result = run_investigation("APPLICANT-001")
    print(result["summary"])
    print("\nRecommendation:", extract_recommendation(result["summary"]))
    print("\n--- Tool calls made ---")
    for call in result["tool_calls"]:
        print(f"{call['tool']}({call['input']}) -> {call['output']}")