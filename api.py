# Thin API layer in front of db/loan_data.db. This is Module 7's FastAPI
# wrapper, merged with the SQLite migration: the 6 structured tools call
# these endpoints over HTTP instead of reading JSON files directly,
# emulating a real microservice/internal-API setup rather than a
# monolithic script reading local files.
#
# search_news is NOT here -- it stays fixture-based pending the
# vector-DB migration, since it's a semantic-search problem, not an
# exact-key lookup like everything else in this file.

import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException

DB_PATH = Path(__file__).parent / "db" / "loan_data.db"

app = FastAPI(title="Loan Due Diligence Data API")


def _query_one(query: str, params: tuple) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


@app.get("/applicants/{applicant_id}/profile")
def get_profile(applicant_id: str):
    row = _query_one(
        "SELECT company_name, industry FROM applicants WHERE applicant_id = ?",
        (applicant_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"No applicant found with id {applicant_id}")
    return row


@app.get("/applicants/{applicant_id}/credit-report")
def get_credit_report(applicant_id: str):
    row = _query_one(
        "SELECT credit_score, late_payments, outstanding_debt FROM credit_reports WHERE applicant_id = ?",
        (applicant_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No credit report on file")
    return row


@app.get("/applicants/{applicant_id}/bank-statements")
def get_bank_statements(applicant_id: str):
    row = _query_one(
        "SELECT avg_monthly_revenue, revenue_volatility, months_of_history FROM bank_statements WHERE applicant_id = ?",
        (applicant_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No bank statements on file")
    return row


@app.get("/applicants/{applicant_id}/business-filings")
def get_business_filings(applicant_id: str):
    row = _query_one(
        "SELECT state_registration_status, tax_filing_status, years_filed_consecutively FROM business_filings WHERE applicant_id = ?",
        (applicant_id,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No business filings on file")
    return row


@app.get("/industry-benchmarks/{industry}")
def get_industry_benchmarks(industry: str):
    row = _query_one(
        "SELECT sector_default_rate, sector_avg_revenue FROM industry_benchmarks WHERE industry = ?",
        (industry,),
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"No benchmark data for industry '{industry}'")
    return row
