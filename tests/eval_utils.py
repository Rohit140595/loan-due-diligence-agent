# Helpers for the hallucination/grounding check (Module 6, Category 2):
# does every number Claude states in its summary actually trace back to
# real tool output data, or did it invent/misstate something?
#
# This is a heuristic, not a proof -- regex-based number extraction from
# free text will have some noise (e.g. it can't tell "3 years" the ground
# truth fact from "3" used as a generic list index). Good enough to catch
# real fabricated numbers; not a substitute for human review of category 3
# (decision quality).

import re


def collect_ground_truth_numbers(tool_calls: list) -> set:
    """
    Walk every tool call's output and collect every numeric leaf value
    (ints/floats). Booleans are excluded -- in Python, bool is a subclass
    of int, so True/False would otherwise leak in as 1/0 and create false
    "matches" against unrelated numbers in the summary.
    """
    numbers = set()

    def walk(value):
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            numbers.add(float(value))
        elif isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    for call in tool_calls:
        walk(call["output"])

    return numbers


# Matches numbers like: 750, 5,000, $5,000, 76.3, 8%, 0.08
_NUMBER_PATTERN = re.compile(r"\$?(\d[\d,]*\.?\d*)%?")


def extract_numbers_from_text(text: str) -> list:
    """
    Extract every number-looking substring from free text, stripping
    currency symbols/commas/percent signs so "$5,000" -> 5000.0 and
    "8%" -> 8.0 (matched separately against the ground-truth's 0.08 --
    see PERCENT handling in matches_ground_truth).
    """
    extracted = []
    for match in _NUMBER_PATTERN.findall(text):
        cleaned = match.replace(",", "")
        if cleaned in ("", "."):
            continue
        extracted.append(float(cleaned))
    return extracted


def matches_ground_truth(extracted: float, ground_truth_values: set, tolerance: float = 0.01) -> bool:
    """
    True if `extracted` is within `tolerance` relative difference of any
    ground-truth value. Handles two real cases from this project:

    1. Zero ground-truth values (e.g. a clamped risk_score of 0) -- can't
       divide by zero to get a relative difference, so 0 only matches 0.
    2. Percentages written two ways -- a sector_default_rate of 0.08 in
       the data might appear as "8%" in the summary (8.0), or rarely as
       "0.08". Check both the raw value and value*100.
    """
    for truth in ground_truth_values:
        candidates = [truth, truth * 100]
        for candidate in candidates:
            if candidate == 0:
                if extracted == 0:
                    return True
                continue
            if abs(extracted - candidate) / abs(candidate) <= tolerance:
                return True
    return False
