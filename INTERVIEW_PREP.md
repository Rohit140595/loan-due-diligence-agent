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

## 10. Technical deep-dive — for drill-down questions

Everything below is read directly from the implementation files, in
enough detail to survive follow-up questions.

### A. The tool-use loop, mechanically (`agent.py`)

Model: `claude-sonnet-4-6`, `temperature=0` (deterministic investigations
— important for both reproducible evals and consistent analyst
experience), `max_tokens=2048`. The loop:

1. `messages` starts as one user turn: `"Investigate loan applicant: {id}"`.
2. Call Claude with `system=STRATEGY, tools=TOOLS, messages=messages`.
3. Check `response.stop_reason`:
   - `"end_turn"` → concatenate all `text`-type content blocks into the
     final summary, return.
   - `"tool_use"` → Claude's response can contain **multiple** `tool_use`
     blocks in one turn (it's allowed to request several tools at once).
     Execute each via `TOOL_FUNCTIONS[block.name](**block.input)`, wrap
     each result as a `tool_result` message keyed by `tool_use_id`
     (this ID pairing is how Claude matches a result back to the request
     that produced it), and send all of them back as **one** new `user`
     message (not one message per tool — they're batched).
   - Anything else (e.g. hitting `max_tokens`) raises — not a state the
     happy path should ever reach.
4. The API is stateless — the full `messages` list is resent, growing,
   on every call. There's no server-side conversation state.

**The trust-boundary point worth stating explicitly**: Claude only ever
*requests* a tool call (a structured `{"name", "input"}` it wants run);
`agent.py`'s own Python code is what actually executes `TOOL_FUNCTIONS[name]`.
Claude cannot do anything beyond exactly what that dict exposes — there's
no code execution, no arbitrary function access, just a fixed dispatch
table.

### B. The LangGraph port, mechanically (`agent_langgraph.py`)

- `StateGraph(MessagesState)` — two nodes: `"agent"` (calls
  `llm.invoke([SystemMessage(STRATEGY)] + state["messages"])`, same
  fresh-system-prompt-every-call behavior as `agent.py`, so swapping the
  underlying model provider wouldn't require restructuring this) and
  `"tools"` (`ToolNode(TOOLS)`, LangGraph's prebuilt tool-executor).
- `tools_condition` is the conditional-edge function that inspects the
  latest message for tool calls and routes to `"tools"` if there are any,
  `END` otherwise — this is the direct structural replacement for
  `agent.py`'s `response.stop_reason == "tool_use"` check.
- Each tool is exposed via LangChain's `@tool` decorator wrapping the
  *same* underlying function from `tools/*.py` — no logic duplicated,
  just re-exposed in LangChain's schema format (derived automatically
  from the docstring + type hints, vs. the hand-written JSON `input_schema`
  in `agent.py`).
- **A real gotcha worth naming if drilled**: `ToolNode` stringifies
  non-string tool outputs (the tools here return dicts/lists) via
  Python's `str()`, not `json.dumps()`. Reconstructing
  `run_investigation`'s `tool_calls` log — needed so the *same* eval
  suite works against both agent versions unchanged — requires
  `ast.literal_eval`, not `json.loads`, to recover the original Python
  object from that stringified form. A subtle, easy-to-miss detail if
  you were porting this yourself.

### C. Data layer specifics

**SQLite** (`db/schema.sql`): 4 tables (`applicants`,
`credit_reports`, `bank_statements`, `business_filings`) keyed by
`applicant_id`, plus `industry_benchmarks` keyed by `industry`. FastAPI
(`api.py`) wraps each with a single-row `SELECT`, opening/closing its own
connection per call (explicitly documented as fine for this app's
low-traffic read-only case, not a production connection-pooling
pattern). Missing data returns **HTTP 404**, which the calling tool
converts into explicit `None` fields rather than an error — the
distinction matters: a brand-new business with no credit history yet
should read to the agent as "checked, there's nothing here" (a real,
informative signal), not as a crash or an omitted field.

**Chroma** (`tools/news_search.py` + `scripts/migrate_news_to_chroma.py`):
each article's embedded document is `"{headline}. {snippet}"` — full
snippet, not just the headline, for more context to match against.
`collection.query()` uses a **fixed, generic risk-oriented query string**
(`"{company_name} negative news lawsuit complaint violation risk concerns"`)
scoped to the applicant via `where={"applicant_id": ...}` metadata
filtering — worth naming candidly as a real limitation if drilled: the
query doesn't adapt based on what the agent has already found elsewhere
in the investigation, it's the same fixed string for every applicant.
No embedding model was explicitly configured — this uses Chroma's
default embedding function, not a custom one; worth checking
`chromadb.utils.embedding_functions` if asked to name it precisely,
since that's a real gap in what's documented in-repo.

### D. The composite risk score formula, exact (`tools/risk_score.py`)

Re-fetches credit/bank/filings/industry data **itself** rather than
trusting values Claude might pass in — explicitly to avoid an LLM
"retyping" a number from earlier context and introducing a transcription
error. If `credit_score` is `None` (no credit history at all), returns
`{"insufficient_data": True, ...}` rather than fabricating a number —
the same "explicit gap, not a guess" principle as the API layer.
Otherwise:

```
base_score  = (credit_score / 850) * 40                         # up to 40 pts
            + (+15 if registration active AND taxes current else -15)
            + (+15 if low revenue volatility, -15 if high, 0 if moderate)
            + (+15 if debt/annual_revenue <= 0.20 else -15)       # -15 if revenue is $0, avoids div-by-zero
            - late_payments * 2
base_score  = clamp(base_score, 0, 100)

sector_multiplier_applied = sector_default_rate >= 0.08 AND credit_score < 750
final_score = base_score * 0.7 if sector_multiplier_applied else base_score
```

The sector multiplier is a genuine design choice worth explaining if
asked: high-default-sector *and* weak personal credit **compounds** as a
30% haircut on top of the base score, rather than the two risk factors
just averaging together additively — the reasoning being that the two
signals reinforcing each other is worse than either alone.

### E. Hallucination detection, both versions (`tests/llm_judge.py`)

Regex-based first attempt: extract numbers from the summary, match
against tool output values. Real false positives on **derived math**
(Claude correctly computing `42000/9000 = 4.7x` — a number that
legitimately doesn't appear verbatim in the evidence) and on
**prompt-stated facts** (a threshold quoted from `strategy.md` itself,
not from tool evidence) — regex pattern-matches digits, it can't
understand arithmetic or source context.

Current version: a **second, independent Claude call** (`temperature=0`,
same model) given the raw tool evidence and the summary, instructed to
flag only claims that state a fact unsupported by the evidence or that
misstate it (explicitly told derived math and qualitative judgment calls
like "weak credit" are fine, not flaggable). Forced to respond in a
strict `{"grounded": bool, "unsupported_claims": [...]}` JSON shape —
with defensive code-fence stripping before `json.loads()`, since Claude
sometimes wraps JSON output in ` ```json ` fences despite being told not
to. Costs one extra billed API call per eval run — a real, acknowledged
tradeoff for actually understanding context instead of pattern-matching.

## 11. Quick reference

| | |
|---|---|
| Tools | 7 total: 6 SQLite+FastAPI (exact lookup), 1 Chroma (semantic search) |
| Orchestration | Raw Anthropic SDK (`agent.py`) + LangGraph port (`agent_langgraph.py`), identical contract |
| Adaptive depth | 3 tool calls (clean) vs. 4-7 (mandatory deep dive) |
| Eval | Behavioral, hallucination/grounding (LLM-as-judge), decision quality vs. human labels |
| Known accepted limitation | `APPLICANT-006` — news-only red flag, documented `xfail`, not a bug |
| Serving | Streamlit UI (`ui.py`), Docker Compose (3 services), 2-tier CI |
| Human role | Final approve/decline decision — regulatory design choice |

## 12. Anticipated questions, one-line pointers

- *"Walk me through the architecture"* → §4.
- *"Why build it raw before using a framework?"* → §5.
- *"How do you know it's not hallucinating?"* → §6 for the summary, §10E for the full mechanics.
- *"Tell me about a limitation you accepted"* → §6's `APPLICANT-006` example — the strongest single story in this project.
- *"Why doesn't the agent make the final decision?"* → §9.
- *"What would you improve with more time?"* → §7 (get the real cost analysis reconstructed and verified) is the honest answer.
- *"Walk me through exactly how the tool-use loop works"* → §10A — know the `stop_reason` check and the multi-tool-per-turn batching cold.
- *"How would you port this to another framework/provider?"* → §10B, especially the `ast.literal_eval` vs `json.loads` gotcha — a good "I actually hit this" detail.
- *"How exactly is risk computed?"* → §10D, you should be able to state the formula from memory.
- *"What embedding model does the news search use?"* → §10C — the honest answer is "Chroma's default, never explicitly configured," which is itself worth naming as an unpinned dependency if asked about reproducibility.
