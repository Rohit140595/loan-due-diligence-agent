"""
Migration script: load fixtures/applicants.json and
fixtures/industry_benchmarks.json into a SQLite database
(db/loan_data.db), replacing direct JSON file reads with real key-based
DB lookups for 5 of the agent's tools (everything except search_news,
which uses a separate vector DB -- see migrate_news_to_chroma.py).

Run with: `python scripts/migrate_to_sqlite.py`

Re-runnable: drops and recreates every table each time, so it's safe to
run again after editing the JSON fixtures during development.
"""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "loan_data.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
APPLICANTS_JSON = ROOT / "fixtures" / "applicants.json"
BENCHMARKS_JSON = ROOT / "fixtures" / "industry_benchmarks.json"


def migrate():
    """
    Rebuild db/loan_data.db from scratch using the current contents of
    fixtures/applicants.json and fixtures/industry_benchmarks.json.
    """
    with open(APPLICANTS_JSON) as f:
        applicants = json.load(f)
    with open(BENCHMARKS_JSON) as f:
        benchmarks = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for table in (
        "applicants",
        "credit_reports",
        "bank_statements",
        "business_filings",
        "industry_benchmarks",
    ):
        cur.execute(f"DROP TABLE IF EXISTS {table}")

    with open(SCHEMA_PATH) as f:
        cur.executescript(f.read())

    for applicant_id, data in applicants.items():
        cur.execute(
            "INSERT INTO applicants (applicant_id, company_name, industry) VALUES (?, ?, ?)",
            (applicant_id, data["company_name"], data["industry"]),
        )

        # Some applicants deliberately have no credit_report (e.g. a
        # brand-new business with no credit history yet) -- skip the
        # insert rather than writing a fabricated row; the API layer
        # returns a "not found" shape that the tool already knows how to
        # turn into None fields, same as the old JSON fallback behavior.
        if "credit_report" in data:
            cr = data["credit_report"]
            cur.execute(
                "INSERT INTO credit_reports (applicant_id, credit_score, late_payments, outstanding_debt) "
                "VALUES (?, ?, ?, ?)",
                (applicant_id, cr["credit_score"], cr["late_payments"], cr["outstanding_debt"]),
            )

        if "bank_statements" in data:
            bs = data["bank_statements"]
            cur.execute(
                "INSERT INTO bank_statements (applicant_id, avg_monthly_revenue, revenue_volatility, months_of_history) "
                "VALUES (?, ?, ?, ?)",
                (applicant_id, bs["avg_monthly_revenue"], bs["revenue_volatility"], bs["months_of_history"]),
            )

        if "business_filings" in data:
            bf = data["business_filings"]
            cur.execute(
                "INSERT INTO business_filings (applicant_id, state_registration_status, tax_filing_status, years_filed_consecutively) "
                "VALUES (?, ?, ?, ?)",
                (
                    applicant_id,
                    bf["state_registration_status"],
                    bf["tax_filing_status"],
                    bf["years_filed_consecutively"],
                ),
            )

    for industry, b in benchmarks.items():
        cur.execute(
            "INSERT INTO industry_benchmarks (industry, sector_default_rate, sector_avg_revenue) VALUES (?, ?, ?)",
            (industry, b["sector_default_rate"], b["sector_avg_revenue"]),
        )

    conn.commit()
    conn.close()
    print(f"Migrated {len(applicants)} applicants and {len(benchmarks)} industry benchmarks to {DB_PATH}")


if __name__ == "__main__":
    migrate()
