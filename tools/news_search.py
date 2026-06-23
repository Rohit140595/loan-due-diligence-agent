# Simulated for this prototype via fixture data. In production this would
# call a real external news API (e.g. Bing News, NewsAPI, GDELT) -- with
# the usual real-world concerns: API cost per call, rate limits, caching
# repeated lookups within an investigation.
#
# Returns RAW articles only -- sentiment/relevance interpretation is the
# agent's job, not this tool's.

import json
from pathlib import Path

FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "applicants.json"


def search_news(applicant_id: str) -> list:
    with open(FIXTURES_PATH) as f:
        applicants = json.load(f)

    applicant = applicants.get(applicant_id)
    if applicant is None:
        return [{"error": f"No applicant found with id {applicant_id}"}]

    return applicant.get("news_articles", [])
