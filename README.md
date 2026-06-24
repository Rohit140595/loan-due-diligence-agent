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
fixtures/         — simulated applicant + industry data (no real PII/APIs)
tools/            — one file per tool, each backed by fixture data:
                      get_applicant_profile, get_credit_report,
                      get_bank_statements, get_business_filings,
                      get_industry_benchmarks, search_news, run_risk_score
agent.py          — the agent loop (raw Anthropic SDK, no framework)
tests/            — eval cases for agent behavior
requirements.txt
```

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=your_key_here" > .env
python agent.py
```

Runs an investigation against the sample applicant in
`fixtures/applicants.json` and prints the structured report.

## Status

End-to-end working: all 6 tools implemented and wired into the agent
loop, verified against a sample applicant. The agent adapts its
investigation depth based on findings and defers the final approve/decline
decision to a human analyst.

Next: cost analysis, eval/hallucination testing against multiple
applicant profiles, FastAPI wrapper.
