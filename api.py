"""
Thin read-only API in front of db/loan_data.db.

Five of the agent's tools (applicant profile, credit report, bank
statements, business filings, industry benchmarks) call these HTTP
endpoints instead of reading JSON files directly -- this emulates a real
internal microservice/data API rather than a script reading local files.

`search_news` is deliberately NOT exposed here: news relevance is a
semantic-similarity problem, not an exact-key lookup like everything in
this file, so it's served from a separate Chroma vector collection
instead (see tools/news_search.py). Each tool uses the storage
technology that actually fits its retrieval pattern.

Run with: `uvicorn api:app --reload`. Requires db/loan_data.db to exist
first -- build it with `python scripts/migrate_to_sqlite.py`.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException

DB_PATH = Path(__file__).parent / "db" / "loan_data.db"

app = FastAPI(title="Loan Due Diligence Data API")


def _query_one(query: str, params: tuple) -> Optional[dict]:
    """
    Run a SELECT expected to return at most one row and return it as a
    plain dict, or None if there were no matching rows. Opens and closes
    its own connection per call -- simple and correct for this app's
    read-only, low-traffic use case; a real production service would
    pool connections instead.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


@app.get("/applicants/{applicant_id}/profile")
def get_profile(applicant_id: str):
    """Company name and industry for one applicant. 404 if unknown."""
    row = _query_one(
        "SELECT company_name, industry FROM applicants WHERE applicant_id = ?",
        (applicant_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"No applicant found with id {applicant_id}")
    return row


@app.get("/applicants/{applicant_id}/credit-report")
def get_credit_report(applicant_id: str):
    """
    Credit score, late payment count, and outstanding debt for one
    applicant. 404 if the applicant has no credit history on file (e.g.
    a brand-new business) -- the calling tool turns that into an
    explicit "no data" result rather than treating it as an error.
    """
    row = _query_one(
        "SELECT credit_score, late_payments, outstanding_debt FROM credit_reports WHERE applicant_id = ?",
        (applicant_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No credit report on file")
    return row


@app.get("/applicants/{applicant_id}/bank-statements")
def get_bank_statements(applicant_id: str):
    """Average monthly revenue, revenue volatility, and months of bank
    history on file for one applicant. 404 if none on file."""
    row = _query_one(
        "SELECT avg_monthly_revenue, revenue_volatility, months_of_history FROM bank_statements WHERE applicant_id = ?",
        (applicant_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No bank statements on file")
    return row


@app.get("/applicants/{applicant_id}/business-filings")
def get_business_filings(applicant_id: str):
    """State registration status, tax filing status, and years filed
    consecutively for one applicant's business. 404 if none on file."""
    row = _query_one(
        "SELECT state_registration_status, tax_filing_status, years_filed_consecutively FROM business_filings WHERE applicant_id = ?",
        (applicant_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No business filings on file")
    return row


@app.get("/industry-benchmarks/{industry}")
def get_industry_benchmarks(industry: str):
    """Sector-level default rate and average revenue for one industry
    (not tied to any individual applicant). 404 if the industry is
    unrecognized."""
    row = _query_one(
        "SELECT sector_default_rate, sector_avg_revenue FROM industry_benchmarks WHERE industry = ?",
        (industry,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"No benchmark data for industry '{industry}'")
    return row
