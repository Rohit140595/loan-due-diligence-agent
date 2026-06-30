# Loan Due Diligence Agent

An agentic AI system that investigates small business loan applications,
adapting its investigation depth based on findings — the same way a human
analyst would, but at scale.

## Business Problem

Manual loan due diligence treats every application the same — analysts
spend equal time on a clean applicant and a suspicious one, which is
expensive and slow. This system adapts its investigation depth based on
what it finds — approving clean applications quickly and spending more
time interrogating red flags.

## Design Principle

The agent investigates and summarizes findings with a recommendation.
A human analyst makes the final approve/decline call. This is a deliberate
choice driven by regulatory requirements and liability in lending — not
a technical limitation.

## Structure

```
strategy.md       — system prompt: overall investigation strategy
fixtures/         — seed data (no real PII/APIs) -- source of truth for
                      both migrations below
db/               — schema.sql + scripts/migrate_to_sqlite.py builds
                      db/loan_data.db; scripts/migrate_news_to_chroma.py
                      builds db/chroma/ (both gitignored, regenerate
                      locally -- see below)
api.py            — thin FastAPI service in front of db/loan_data.db
tools/            — one file per tool:
                      get_applicant_profile, get_credit_report,
                      get_bank_statements, get_business_filings,
                      get_industry_benchmarks  -> call api.py over HTTP
                      search_news                -> queries db/chroma/
                        directly (semantic search, no API layer needed)
                      run_risk_score              -> pure computation,
                        calls the other tool functions directly (no I/O
                        of its own)
agent.py          — the agent loop (raw Anthropic SDK, no framework)
agent_langgraph.py — same agent, ported to LangGraph (see "Raw SDK vs
                      LangGraph" below) -- run with `python
                      agent_langgraph.py`, traced automatically to
                      LangSmith if LANGCHAIN_TRACING_V2=true
eval_langsmith.py — small LangSmith dataset + evaluate() demo (2 of the
                      7 labeled applicants) -- separate from, not a
                      replacement for, tests/test_agent.py
ui.py             — Streamlit UI: pick an applicant, run the agent,
                      review the report + full tool-call audit trail
tests/            — eval suite (behavioral correctness, hallucination/
                      grounding via LLM-as-judge, decision quality
                      against human-labeled fixtures)
requirements.txt
```

## Raw SDK vs. LangGraph

`agent.py` is built directly on the Anthropic SDK -- no framework --
specifically so the actual mechanics of tool use (Claude requests a
tool call, your code executes it, the result goes back as a new
message, repeat until done) stay visible rather than hidden behind
abstractions.

`agent_langgraph.py` is the same agent ported to LangGraph once those
mechanics were already understood and tested. It's mechanically
identical -- same tools, same `strategy.md` system prompt, same
stop/continue logic -- only the orchestration code changed: the
hand-written `while True` loop becomes a 2-node graph (`agent` calls
Claude, `tools` executes whatever it requested) with a conditional edge
back to `agent`, using LangGraph's prebuilt `ToolNode` and
`tools_condition` instead of the manual dispatch logic in `agent.py`.
Both versions expose the same `run_investigation(applicant_id)`
contract (`{"summary": ..., "tool_calls": [...]}`), so downstream code
like `extract_recommendation()` works unchanged against either one.

The payoff of building raw first: LangChain's `@tool` decorator derives
each tool's schema from its docstring and type hints automatically
(rather than the hand-written JSON `TOOLS` list in `agent.py`), and
LangSmith traces every step automatically just by setting
`LANGCHAIN_TRACING_V2=true` -- because LangChain/LangGraph components
already expose a common interface the tracer hooks into. Neither of
those is "free" in the raw version; they're the direct payoff of
adopting the framework's structure, not something for nothing.

## Data storage: why SQLite + FastAPI for 5 tools, a vector DB for 1

5 of the 6 structured tools are exact key-based lookups (`applicant_id`
-> record, `industry` -> benchmark) -- that's what a relational DB and a
thin API layer are for, emulating how a real lending backend would be
wired (an internal API in front of a database), not a script reading
local JSON.

`search_news` is deliberately different: news relevance is a
semantic-similarity problem, not an exact-match one, so it's backed by a
Chroma vector collection instead -- queried by embedding similarity
(scoped to the right applicant via metadata filtering), the same shape a
real news API's relevance ranking would have. Using a vector store for
the other 5 tools would be the wrong tool for an exact-lookup job, and
using SQLite for news would lose the ability to rank by relevance at all.

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# Build both local databases from fixtures/ (gitignored; regenerate
# after editing fixtures/applicants.json or industry_benchmarks.json)
python scripts/migrate_to_sqlite.py
python scripts/migrate_news_to_chroma.py

# Start the data API (separate terminal, leave running -- only needed
# for the 5 SQLite-backed tools; search_news queries Chroma directly)
uvicorn api:app --reload

# Run the agent from the command line...
python agent.py

# ...or launch the UI instead (same prerequisites: API server + both DBs)
streamlit run ui.py

# ...or run the LangGraph port instead of the raw version
python agent_langgraph.py

# Optional: also requires LANGCHAIN_API_KEY in .env to enable tracing
# and the eval dataset below
echo "LANGCHAIN_API_KEY=your_key_here" >> .env
echo "LANGCHAIN_TRACING_V2=true" >> .env
echo "LANGCHAIN_PROJECT=loan-due-diligence-agent" >> .env

# Run a small LangSmith dataset eval (2 applicants) against the
# LangGraph version -- prints a link to the results dashboard
python eval_langsmith.py
```

The CLI run investigates the sample applicant in
`fixtures/applicants.json` and prints the structured report. The UI lets
you pick any applicant from a dropdown, run the investigation, and
review the report alongside a full audit trail of every tool call the
agent made. The eval suite (`pytest tests/test_agent.py`) also requires
the API server running.

## Status

End-to-end working: all 6 tools implemented and wired into the agent
loop. Data for 5 tools flows through SQLite + a thin FastAPI layer;
`search_news` flows through a Chroma vector collection -- each tool
backed by the storage technology that actually fits its retrieval
pattern, rather than one technology used everywhere. The agent adapts
its investigation depth based on findings and defers the final
approve/decline decision to a human analyst. Full eval suite covers
behavioral correctness, hallucination/grounding, and decision quality
against human-labeled fixtures. A Streamlit UI (`ui.py`) provides a
human-facing view of the same investigation flow. A LangGraph port
(`agent_langgraph.py`) demonstrates the same agent on a standard
orchestration framework with automatic LangSmith tracing and a small
dataset-based eval (`eval_langsmith.py`), built deliberately after the
raw version so the framework's value-add (and what it costs in
implicit behavior) could be evaluated directly.
