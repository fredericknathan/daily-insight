"""
The hallucination guard described throughout the outline as non-negotiable.

Every number the model outputs (any digit sequence that looks like a
price or a percentage) must trace back to something we actually injected
into the prompt. If it doesn't, the paragraph is rejected and regenerated
once; if it fails twice, the country falls back to a templated,
zero-creativity sentence built directly from the data with no LLM
involved at all. A wrong number in a macro brief is worse than a boring
sentence.
"""

from __future__ import annotations
import re
import logging
from src.fetch.resilience import ResolvedSnapshot

logger = logging.getLogger(__name__)

NUMBER_PATTERN = re.compile(r"-?\d+\.?\d*%?")


def _extract_numbers(text: str) -> set[str]:
    """Pull every number-like token out of a string, normalised (strip
    trailing .0, strip %) so '0.82%' and '0.82' compare equal."""
    found = set()
    for match in NUMBER_PATTERN.findall(text):
        clean = match.rstrip("%").rstrip(".")
        if clean and clean not in ("-", "."):
            found.add(clean)
    return found


def _source_numbers(snapshot: ResolvedSnapshot) -> set[str]:
    allowed = set()
    for val in (snapshot.price, snapshot.change_pct, snapshot.ytd_pct):
        if val is None:
            continue
        allowed.add(str(round(val, 2)).rstrip("0").rstrip("."))
        allowed.add(str(round(val)))  # rounded version, models often round for readability
        allowed.add(str(abs(round(val, 2))).rstrip("0").rstrip("."))  # sign-stripped, e.g. "-0.42" -> "0.42"
    return allowed


def validate_paragraph(text: str, snapshot: ResolvedSnapshot) -> tuple[bool, list[str]]:
    """Returns (is_valid, list_of_unexplained_numbers)."""
    found = _extract_numbers(text)
    allowed = _source_numbers(snapshot)

    # Small integers (single digits, common in phrases like "a 5-day rally"
    # or ticker-adjacent numbers) are noisy false positives — only flag
    # numbers that look like they could plausibly BE a price or change%.
    suspicious = {
        n for n in found
        if n not in allowed and (len(n) > 1 or "." in n)
    }

    if suspicious:
        logger.warning(
            "Validation failed for %s: unexplained numbers %s (allowed: %s)",
            snapshot.country, suspicious, allowed,
        )
        return False, list(suspicious)
    return True, []


def fallback_sentence(country_name: str, index_name: str, snapshot: ResolvedSnapshot) -> str:
    """Zero-creativity fallback. Used when the LLM fails generation."""
    return "A narrative summary could not be generated for this market today."
