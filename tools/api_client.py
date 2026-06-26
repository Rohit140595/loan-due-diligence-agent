# Shared HTTP client for the 5 tools that now call api.py instead of
# reading fixtures/applicants.json directly. Centralizing this avoids
# repeating the same requests.get/error-handling logic in every tool
# file.

import os

import requests

API_BASE_URL = os.environ.get("LOAN_API_BASE_URL", "http://localhost:8000")


def api_get(path: str):
    """
    GET a path from the data API. Returns the parsed JSON dict on 200,
    or None on 404 (e.g. an applicant with no credit history) -- callers
    turn that into the same None-filled fallback dict the old JSON-based
    tools returned, so nothing downstream (agent.py, strategy.md) needs
    to change.
    """
    response = requests.get(f"{API_BASE_URL}{path}", timeout=5)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()
