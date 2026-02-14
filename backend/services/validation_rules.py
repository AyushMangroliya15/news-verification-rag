"""
Validation rules: cite-only, no cite -> NEE, min evidence.
Ensures we never return Supported/Refuted without sufficient citations from the evidence set.
"""

from typing import List, Tuple

from backend.constants import MIN_EVIDENCE_COUNT, Verdict
from backend.models import Citation


def apply_validation_rules(
    proposed_verdict: str,
    reasoning: str,
    citations: List[Citation],
    allowed_urls: set[str],
    min_sources: int = MIN_EVIDENCE_COUNT,
) -> Tuple[str, str, List[Citation]]:
    """
    Enforce: (1) only cite URLs in allowed_urls, (2) Supported/Refuted require
    at least min_sources citations else force Not Enough Evidence.
    Returns (final_verdict, final_reasoning, filtered_citations).
    """
    verdict_norm = (proposed_verdict or "").strip()
    if verdict_norm not in (Verdict.SUPPORTED.value, Verdict.REFUTED.value):
        # For NEE, Mixed, Unverifiable we only filter citations
        filtered = [c for c in citations if c.url in allowed_urls]
        return verdict_norm or Verdict.NOT_ENOUGH_EVIDENCE.value, reasoning, filtered

    # Supported or Refuted: filter citations to allowed set
    filtered = [c for c in citations if c.url in allowed_urls]
    if len(filtered) < min_sources:
        return (
            Verdict.NOT_ENOUGH_EVIDENCE.value,
            reasoning
            + " Insufficient cited sources to support this verdict; reporting Not Enough Evidence."
            if reasoning
            else "Insufficient cited sources; reporting Not Enough Evidence.",
            filtered,
        )
    return verdict_norm, reasoning, filtered
