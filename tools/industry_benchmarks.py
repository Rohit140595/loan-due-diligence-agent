# Sector-level reference data -- not tied to any individual applicant,
# so this reads from its own fixture file keyed by industry, not by
# applicant_id.

import json
from pathlib import Path

FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "industry_benchmarks.json"


def get_industry_benchmarks(industry: str) -> dict:
    with open(FIXTURES_PATH) as f:
        benchmarks = json.load(f)

    return benchmarks.get(industry, {
        "error": f"No benchmark data found for industry '{industry}'"
    })
