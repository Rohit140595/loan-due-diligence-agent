"""
Shared HTTP client used by the 5 tools that call api.py (the FastAPI
service in db/loan_data.db's place) instead of reading
fixtures/applicants.json directly. Centralizing the request/error
handling here avoids repeating it in every tool file.

Requires the API server to be running (`uvicorn api:app --reload`)
before any of those tools are called.
"""

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
