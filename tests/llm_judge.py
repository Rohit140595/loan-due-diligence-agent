# LLM-as-judge grounding check (Module 6, Category 2).
#
# A first attempt used regex to extract numbers from the summary and
# match them against tool output values, but that had real false
# positives on derived math (e.g. Claude correctly computing
# "42000/9000 = 4.7x") and prompt-stated facts (e.g. a threshold from
# strategy.md), since regex can't understand context or arithmetic, only
# pattern-match digits.
#
# This uses a second, independent Claude call to judge whether the
# agent's summary is factually supported by the tool evidence -- it
# understands derived math and context the way a human reviewer would.
# Tradeoff: costs an extra API call per eval run (see Module 5).

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()
_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
_MODEL = "claude-sonnet-4-6"

JUDGE_PROMPT = """You are a fact-checker. You will be given EVIDENCE (raw \
data from tool calls) and a SUMMARY (a report written by another AI based \
on that evidence).

Check whether every factual claim in the SUMMARY is actually supported by \
the EVIDENCE. This includes:
- Direct values (e.g. "credit score of 610" must match the evidence)
- Correct derived math (e.g. "4.7x revenue" from 42000/9000 is fine if the \
arithmetic is correct)
- Reasonable qualitative interpretation (e.g. calling a credit score \
"weak" is fine, that's judgment, not a fact claim)

Flag ONLY claims that state a fact/number not supported by the evidence \
or that misstate the evidence (e.g. wrong arithmetic, a number that \
doesn't appear anywhere in the evidence).

Respond with ONLY valid JSON, no other text, in this exact shape:
{"grounded": true or false, "unsupported_claims": ["...", "..."]}

EVIDENCE:
__EVIDENCE__

SUMMARY:
__SUMMARY__
"""


def judge_grounding(tool_calls: list, summary: str) -> dict:
    evidence = json.dumps(
        [{"tool": c["tool"], "output": c["output"]} for c in tool_calls],
        indent=2,
    )

    response = _client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": JUDGE_PROMPT.replace("__EVIDENCE__", evidence).replace(
                    "__SUMMARY__", summary
                ),
            }
        ],
    )

    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    # Claude sometimes wraps JSON in a code fence despite instructions --
    # strip it defensively rather than letting json.loads crash.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    return json.loads(raw_text)
