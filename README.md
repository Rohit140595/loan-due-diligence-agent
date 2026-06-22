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
tools/            — one file per tool (simulated data sources)
agent.py          — the agent loop (tool use orchestration)
tests/            — eval cases for agent behavior
requirements.txt
```

## Status

Work in progress — built as a learning project for agentic AI concepts.
