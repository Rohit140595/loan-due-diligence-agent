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
                      the SQLite migration; search_news still reads this
                      directly (see "Data storage" below)
db/               — schema.sql + scripts/migrate_to_sqlite.py builds
                      db/loan_data.db from fixtures/ (gitignored, regenerate
                      locally -- see below)
api.py            — thin FastAPI service in front of db/loan_data.db
tools/            — one file per tool:
                      get_applicant_profile, get_credit_report,
                      get_bank_statements, get_business_filings,
                      get_industry_benchmarks  -> call api.py over HTTP
                      search_news                -> still fixture-based
                      run_risk_score              -> pure computation,
                        calls the other tool functions directly (no I/O
                        of its own)
agent.py          — the agent loop (raw Anthropic SDK, no framework)
tests/            — eval suite (behavioral correctness, hallucination/
                      grounding via LLM-as-judge, decision quality
                      against human-labeled fixtures)
requirements.txt
```

## Data storage: why SQLite + FastAPI, not one technology for everything

5 of the 6 structured tools are exact key-based lookups (`applicant_id`
-> record, `industry` -> benchmark) -- that's what a relational DB and a
thin API layer are for, emulating how a real lending backend would be
wired (an internal API in front of a database), not a script reading
local JSON. `search_news` is deliberately different: news relevance is a
semantic-similarity problem, not an exact-match one, so it's a candidate
for a vector DB later rather than SQLite -- using a vector store for the
other 5 tools would be the wrong tool for an exact-lookup job.

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=your_key_here" > .env

# Build the local database from fixtures/ (gitignored; regenerate after
# editing fixtures/applicants.json or industry_benchmarks.json)
python scripts/migrate_to_sqlite.py

# Start the data API (separate terminal, leave running)
uvicorn api:app --reload

# Run the agent (talks to the API above + Anthropic API)
python agent.py
```

Runs an investigation against the sample applicant in
`fixtures/applicants.json` and prints the structured report. The eval
suite (`pytest tests/test_agent.py`) also requires the API server running.

## Status

End-to-end working: all 6 tools implemented and wired into the agent
loop. Data for 5 of the 6 tools now flows through SQLite + a thin
FastAPI layer instead of direct JSON reads, closer to a real production
setup. The agent adapts its investigation depth based on findings and
defers the final approve/decline decision to a human analyst. Full eval
suite covers behavioral correctness, hallucination/grounding, and
decision quality against human-labeled fixtures.

Next: vector DB for search_news, UI layer to display results.
