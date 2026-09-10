# Interview Prep — Loan Due Diligence Agent

Everything below is grounded in this repo's actual code (`README.md`,
`strategy.md`, `tools/`, `tests/`, `.github/workflows/`) as of the last
commit (2026-06-29), not summarized from memory. One figure is flagged
below as unverified — see §7.

## 1. The 30-second pitch

*"I built an agentic AI system that investigates small business loan
applications the way a human analyst would — adapting how much digging
it does based on what it finds, rather than treating every application
identically. Clean applicants get approved after 3 targeted checks;
anything ambiguous or risky triggers a mandatory deeper investigation
across at least 4 of 7 available tools. I built it twice — once on the
raw Anthropic SDK to keep the tool-use mechanics fully visible, then
ported it to LangGraph to compare what a framework actually buys you.
Human analysts still make the final call; the agent's job is the
investigative legwork, not the decision — that's a deliberate,
regulatory-driven design choice, not a limitation."*

## 2. The business problem, precisely

Manual loan due diligence spends the same analyst time on a clean
applicant as a suspicious one — expensive and slow at scale. The agent's
entire value proposition is **adaptive depth**: spend less on the easy
cases, more on the ones that actually need it. This is the single idea
to anchor every other answer back to.

## 3. The adaptive-depth mechanic — exact logic, from `strategy.md`

- Always call `get_credit_report` and `get_bank_statements` first.
- **Stop-early path** (3 tool calls total): if credit score ≥720, 0-2
  late payments, low debt-to-revenue, and low/moderate revenue
  volatility, call `get_business_filings` as a mandatory compliance
  check (good credit never excuses skipping it — tax delinquency, e.g.,
  is invisible in credit/bank data). If filings are also clean, stop and
  recommend from just those three results.
- **Otherwise, mandatory deeper investigation**: at least 4 of the 7
  tools, specifically including `get_business_filings` and
  `run_risk_score`, before any DECLINE or ESCALATE recommendation. A bad
  credit report *alone* is explicitly **not** sufficient evidence for
  DECLINE in the system prompt — the agent is instructed not to
  short-circuit on a single bad signal.
- The system prompt is explicit that minimizing tool calls is "a primary
  objective, not an optional nice-to-have," and that calling a tool "just
  to be thorough" when evidence is already clear is a **failure** of the
  task, not a safe default. Good detail if asked "how did you prevent
  the agent from just being maximally cautious" — the prompt actively
  penalizes that instinct.

## 4. Architecture — 7 tools, 2 storage technologies, matched to the retrieval pattern

6 structured tools (`applicant_profile`, `credit_report`,
`bank_statements`, `business_filings`, `industry_benchmarks`,
`risk_score`) are exact key-based lookups — backed by SQLite behind a
thin FastAPI layer, emulating how a real lending backend would actually
be wired (an internal API in front of a database), not a script reading
local JSON. `search_news` is different in kind: news relevance is a
semantic-similarity problem, not an exact match, so it's backed by a
Chroma vector collection instead, queried by embedding similarity scoped
to the applicant via metadata filtering. `run_risk_score` is pure
computation — it calls the other tool functions directly rather than
doing its own I/O.

**The reasoning to lead with if asked "why two different storage
technologies"**: using a vector store for the 6 exact-lookup tools would
be the wrong tool for the job (unnecessary embedding overhead for
something a primary-key lookup already solves); using SQLite for news
would lose the ability to rank by relevance entirely, since relevance
*is* the whole point of that tool.

## 5. Raw SDK vs. LangGraph — built in that order deliberately

`agent.py` is a hand-written `while True` tool-use loop directly on the
Anthropic SDK — no framework — specifically so the actual mechanics
(Claude requests a tool call → your code executes it → the result goes
back as a new message → repeat) stay visible. `agent_langgraph.py` is
the same agent, ported *after* those mechanics were already understood:
same tools, same `strategy.md` prompt, same stop/continue logic — only
the orchestration changed, into a 2-node graph (`agent` calls Claude,
`tools` executes) with a conditional edge back to `agent`, using
LangGraph's prebuilt `ToolNode`/`tools_condition`. Both expose an
identical `run_investigation(applicant_id)` contract, so downstream code
works unchanged against either.

**The tradeoff worth naming explicitly**: LangChain's `@tool` decorator
derives each tool's schema from docstring + type hints automatically
(vs. the hand-written JSON schema in `agent.py`), and LangSmith traces
every step automatically via `LANGCHAIN_TRACING_V2=true` — but neither of
those is "free," they're the direct payoff of adopting the framework's
structure and its conventions, not something you get without buying into
it. Building raw first is what makes you able to say *why* the framework
version's automatic behavior works, not just that it does.

## 6. Evaluation — three categories, `tests/test_agent.py` + `tests/llm_judge.py`

- **Behavioral correctness**: does the agent follow the stop-early /
  mandatory-deep-dive logic from `strategy.md` for a given applicant
  profile.
- **Hallucination / grounding**: is every claim in the agent's summary
  actually traceable to a tool result — via LLM-as-judge
  (`tests/llm_judge.py`), an upgrade from an earlier regex-based
  approach that had false positives on the agent's own derived math
  (e.g. computing a ratio from two tool results correctly, but the regex
  couldn't tell that from an unsupported claim).
- **Decision quality**: agent recommendation vs. human-labeled ground
  truth (`tests/decision_labels.json`). Deliberately asymmetric: a false
  APPROVE (should have been ESCALATE/DECLINE) is treated as the dangerous
  failure direction and is a hard test failure; being *more* conservative
  than the label (label says APPROVE, agent says ESCALATE) is tolerated
  as an efficiency loss, not a safety failure.

**A concrete, honest example to bring up unprompted** — `APPLICANT-006`
is an accepted, documented limitation (`xfail` in the test suite, not a
silently-passing or silently-skipped test): its only red flag lives in
news, but `search_news` isn't a mandatory pre-APPROVE check the way
`get_business_filings` is. The tradeoff was judged deliberately: making
every discovered blind spot a new mandatory check converges toward
"call all 7 tools on every applicant," which defeats the entire
adaptive-depth value proposition the agent exists for. This is the
single best answer in this whole project for "tell me about a limitation
you knowingly accepted and why."

## 7. Cost / ROI — verify before citing a specific number

Earlier project notes describe a cost comparison (~$0.044/application in
API cost vs. ~$6.67 in analyst time at 1000 applications/month, ~100x
ROI) and the README references a "Module 5 cost analysis" by name — but
that calculation isn't present anywhere in this repo's committed history
(checked full `git log -p`). **Don't cite the specific numbers in an
interview without reconstructing them first** — the *shape* of the
argument (adaptive depth means the agent's own API cost scales down for
easy cases, same as analyst time would; compare average tokens-per-
investigation × current Claude pricing against a loaded analyst hourly
rate) is sound and worth explaining, but the precise multiplier needs
recomputing against current pricing before it goes in front of an
interviewer.

## 8. Production-readiness signals (verified from `README.md` / git log, newer than earlier notes)

- **Docker**: 3-service `docker-compose` (`migrate` → `api` → `ui`),
  `db/` bind-mounted so containerized and local runs land in the same
  place.
- **2-tier CI**: `ci-fast.yml` runs free syntax/import checks on every
  push; `ci-eval.yml` runs the real, billed agent eval suite
  (`pytest tests/test_agent.py`) only on pushes to `main` — gating the
  expensive suite to already-reviewed, merged code rather than every WIP
  push. Good detail for "how do you think about CI cost with an LLM in
  the loop."

## 9. Design principle worth stating unprompted: human-in-the-loop is regulatory, not a limitation

The agent investigates and recommends; a human analyst makes the final
approve/decline call. `README.md` states this is "driven by regulatory
requirements and liability in lending — not a technical limitation." If
asked "could the agent just decide," the answer isn't "not yet" — it's
"deliberately not its job."

## 10. Quick reference

| | |
|---|---|
| Tools | 7 total: 6 SQLite+FastAPI (exact lookup), 1 Chroma (semantic search) |
| Orchestration | Raw Anthropic SDK (`agent.py`) + LangGraph port (`agent_langgraph.py`), identical contract |
| Adaptive depth | 3 tool calls (clean) vs. 4-7 (mandatory deep dive) |
| Eval | Behavioral, hallucination/grounding (LLM-as-judge), decision quality vs. human labels |
| Known accepted limitation | `APPLICANT-006` — news-only red flag, documented `xfail`, not a bug |
| Serving | Streamlit UI (`ui.py`), Docker Compose (3 services), 2-tier CI |
| Human role | Final approve/decline decision — regulatory design choice |

## 11. Anticipated questions, one-line pointers

- *"Walk me through the architecture"* → §4.
- *"Why build it raw before using a framework?"* → §5.
- *"How do you know it's not hallucinating?"* → §6, name the regex→LLM-judge upgrade.
- *"Tell me about a limitation you accepted"* → §6's `APPLICANT-006` example — the strongest single story in this project.
- *"Why doesn't the agent make the final decision?"* → §9.
- *"What would you improve with more time?"* → §7 (get the real cost analysis reconstructed and verified) is the honest answer.
