-- Structured, exact-key-lookup data for the 6 non-news tools. This is a
-- relational store on purpose -- every lookup here is "give me the record
-- for this applicant_id / this industry", not a similarity search, so a
-- relational DB is the right tool (see README for the news/vector-DB
-- split rationale).

CREATE TABLE IF NOT EXISTS applicants (
    applicant_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    industry TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS credit_reports (
    applicant_id TEXT PRIMARY KEY REFERENCES applicants(applicant_id),
    credit_score INTEGER,
    late_payments INTEGER,
    outstanding_debt REAL
);

CREATE TABLE IF NOT EXISTS bank_statements (
    applicant_id TEXT PRIMARY KEY REFERENCES applicants(applicant_id),
    avg_monthly_revenue REAL,
    revenue_volatility TEXT,
    months_of_history INTEGER
);

CREATE TABLE IF NOT EXISTS business_filings (
    applicant_id TEXT PRIMARY KEY REFERENCES applicants(applicant_id),
    state_registration_status TEXT,
    tax_filing_status TEXT,
    years_filed_consecutively INTEGER
);

CREATE TABLE IF NOT EXISTS industry_benchmarks (
    industry TEXT PRIMARY KEY,
    sector_default_rate REAL,
    sector_avg_revenue REAL
);
