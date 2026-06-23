# TODO (Module 4): build the agent loop here.
import anthropic
from dotenv import load_dotenv
import os
import json

from tools import (
    get_applicant_profile
    , get_bank_statements
    , get_credit_report
    , get_business_filings
    , get_industry_benchmarks
    # , search_news             # TODO: open design question -- what powers this for real?
    # , run_risk_score          # TODO: not implemented yet
    )

# Load ENV
load_dotenv()  # reads .env into environment variables

# API Key
API_KEY = os.environ["ANTHROPIC_API_KEY"]
client = anthropic.Anthropic(api_key=API_KEY)
MODEL = "claude-sonnet-4-6"

# 1. Load strategy.md contents -> use as the `system` prompt
with open("strategy.md") as f:
    STRATEGY = f.read()

# 2. Define the `tools` list (name, description, input_schema) for each
#    function in tools/. This is what we send to Claude so it knows what
#    it's allowed to call and what arguments each tool expects.
TOOLS = [
    {
        "name": "get_applicant_profile",
        "description": "Fetch the applicant's basic profile (company name, industry) for the given applicant id.",
        "input_schema": {
            "type": "object",
            "properties": {"applicant_id": {"type": "string"}},
            "required": ["applicant_id"],
        },
    },
    {
        "name": "get_credit_report",
        "description": "Fetch the applicant's credit report (score, late payments, outstanding debt).",
        "input_schema": {
            "type": "object",
            "properties": {"applicant_id": {"type": "string"}},
            "required": ["applicant_id"],
        },
    },
    {
        "name": "get_bank_statements",
        "description": "Fetch summarized bank statement data (avg monthly revenue, revenue volatility, months of history).",
        "input_schema": {
            "type": "object",
            "properties": {"applicant_id": {"type": "string"}},
            "required": ["applicant_id"],
        },
    },
    {
        "name": "get_business_filings",
        "description": "Fetch state registration / incorporation / tax filing status for the business.",
        "input_schema": {
            "type": "object",
            "properties": {"applicant_id": {"type": "string"}},
            "required": ["applicant_id"],
        },
    },
    {
        "name": "get_industry_benchmarks",
        "description": "Fetch sector-level benchmarks (default rate, average revenue) for the applicant's industry.",
        "input_schema": {
            "type": "object",
            "properties": {"industry": {"type": "string"}},
            "required": ["industry"],
        },
    },
    # TODO: open design questions -- see search_news / run_risk_score below
    # {
    #     "name": "search_news",
    #     "description": "Search recent news/articles mentioning the company. Returns raw snippets for the agent to interpret.",
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {"company_name": {"type": "string"}},
    #         "required": ["company_name"],
    #     },
    # },
    # {
    #     "name": "run_risk_score",
    #     "description": "Compute a composite risk score from whatever evidence has been gathered so far.",
    #     "input_schema": {
    #         "type": "object",
    #         "properties": {"evidence": {"type": "object"}},
    #         "required": ["evidence"],
    #     },
    # },
]

# Maps each tool name Claude can request -> the actual Python function to run.
# Keys here must match the "name" fields in TOOLS exactly.
TOOL_FUNCTIONS = {
    "get_applicant_profile": get_applicant_profile,
    "get_credit_report": get_credit_report,
    "get_bank_statements": get_bank_statements,
    "get_business_filings": get_business_filings,
    "get_industry_benchmarks": get_industry_benchmarks,
    # "search_news": search_news,                       # TODO: open design question
    # "run_risk_score": run_risk_score,                 # TODO: not implemented yet
}


def call_claude(messages):
    """
    Send the current conversation (messages) to Claude, along with the
    system prompt and tool definitions. Returns Claude's response.
    """
    return client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=STRATEGY,
        tools=TOOLS,
        messages=messages,
    )


def run_investigation(applicant_id):
    # 3. Send initial message (applicant_id) to Claude with system + tools.
    # `messages` holds the entire conversation. The API is stateless, so we
    # resend this whole list (with everything appended so far) on every call.
    messages = [
        {"role": "user", "content": f"Investigate loan applicant: {applicant_id}"}
    ]

    # 4. Loop:
    #       - if Claude's response contains a tool_use block:
    #           - execute the corresponding Python function from tools/
    #           - send the result back as a tool_result message
    #       - if Claude's response is plain text (final summary):
    #           - stop the loop, return the result
    while True:
        response = call_claude(messages)

        # Record exactly what Claude said (text and/or tool_use blocks) so
        # the next call has full context.
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Claude is done -- no more tools requested. Collect its text
            # blocks into the final summary and return.
            return "".join(
                block.text for block in response.content if block.type == "text"
            )

        elif response.stop_reason == "tool_use":
            # Claude can request multiple tools in a single turn. We must
            # run each one and reply with a tool_result for each, bundled
            # into a single new "user" message.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                func = TOOL_FUNCTIONS[block.name]
                result = func(**block.input)

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )

            messages.append({"role": "user", "content": tool_results})

        else:
        # e.g. max_tokens or stop_sequence -- shouldn't happen in normal use.
            raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason}")


# Keep this loop visible and simple at first -- no framework (LangChain/etc)
# so the mechanics from Module 2 stay obvious.

if __name__ == "__main__":
    summary = run_investigation("APPLICANT-001")
    print(summary)
