"""
Evidence evaluation: sufficiency, stance classification, conflict detection.
"""
from __future__ import annotations

import json
import logging
from typing import List, Literal

from openai import OpenAI

from backend.config import MIN_SOURCES_FOR_VERDICT, OPENAI_API_KEY, OPENAI_LLM_MODEL
from backend.constants import STANCE_NEUTRAL, STANCE_REFUTES, STANCE_SUPPORTS
from backend.models import EvidenceItem

logger = logging.getLogger(__name__)

StanceLabel = Literal["supports", "refutes", "neutral"]


def _extract_stance_array(text: str) -> list | None:
    """
    Extract a JSON array of stance labels from LLM response.
    Handles raw '[...]' or markdown-wrapped (e.g. ```json\\n[...]```).
    Returns list of strings or None if parsing fails.
    """
    if not text or not text.strip():
        return None
    s = text.strip()
    # Strip markdown code block if present
    if s.startswith("```"):
        lines = s.split("\n")
        # Drop first line (```json or ```) and trailing ```
        if len(lines) > 1:
            rest = "\n".join(lines[1:])
            if rest.endswith("```"):
                rest = rest[:-3].strip()
            s = rest
    # Find first '[' and matching ']' to extract array
    start = s.find("[")
    if start == -1:
        return None
    depth = 0
    for i, c in enumerate(s[start:], start=start):
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                try:
                    arr = json.loads(s[start : i + 1])
                    if isinstance(arr, list):
                        return arr
                except (json.JSONDecodeError, TypeError):
                    pass
                return None
    return None


def is_sufficient(
    evidence: List[EvidenceItem],
    min_sources: int | None = None,
) -> bool:
    """True if evidence has at least min_sources items (default from config)."""
    n = min_sources if min_sources is not None else MIN_SOURCES_FOR_VERDICT
    return len(evidence) >= n


def _classify_stances_batch(claim: str, items: List[EvidenceItem]) -> List[StanceLabel]:
    """Call LLM once to classify stance for each snippet. Returns list in same order as items."""
    if not items or not OPENAI_API_KEY:
        return [STANCE_NEUTRAL] * len(items)
    snippets = [item.snippet or item.title or "" for item in items]
    prompt = f"""You are a fact-checking assistant. For the following CLAIM, classify each SOURCE snippet as exactly one of: supports, refutes, neutral.
- supports: the source clearly supports or confirms the claim.
- refutes: the source clearly contradicts or debunks the claim.
- neutral: the source does not clearly support or refute, or is irrelevant.

CLAIM: {claim[:500]}

SOURCES (one per line, prefixed by index):
"""
    for i, snip in enumerate(snippets[:30]):  # cap to avoid token limit
        prompt += f"\n{i}: {snip[:400]}\n"
    prompt += "\nRespond with a JSON array of exactly one word per source in order: only \"supports\", \"refutes\", or \"neutral\". Example: [\"neutral\", \"refutes\", \"supports\"]"

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        text = (resp.choices[0].message.content or "").strip()
        # Parse JSON array: accept raw "[...]" or markdown-wrapped (e.g. ```json\n[...]```
        arr = _extract_stance_array(text)
        if arr is not None:
            out: List[StanceLabel] = []
            for x in arr:
                s = (str(x).lower() if x is not None else "").strip()
                if s in ("supports", "refutes", "neutral"):
                    out.append(s)
                else:
                    out.append(STANCE_NEUTRAL)
            # Pad to len(items) if LLM returned fewer
            while len(out) < len(items):
                out.append(STANCE_NEUTRAL)
            return out[: len(items)]
        # LLM did not return a parseable JSON array (e.g. wrong format or wrapped in markdown)
        logger.debug(
            "Stance classification: no JSON array in response (first 200 chars): %s",
            text[:200],
        )
        return [STANCE_NEUTRAL] * len(items)
    except Exception as e:
        logger.warning("Stance classification failed: %s", e)
        return [STANCE_NEUTRAL] * len(items)


def attach_stances(claim: str, evidence: List[EvidenceItem]) -> None:
    """Classify and set stance on each EvidenceItem in place."""
    if not evidence:
        return
    stances = _classify_stances_batch(claim, evidence)
    if not stances:
        stances = [STANCE_NEUTRAL] * len(evidence)
    for i, item in enumerate(evidence):
        item.stance = stances[i] if i < len(stances) else STANCE_NEUTRAL


def has_conflict(evidence: List[EvidenceItem], claim: str) -> bool:
    """True if at least one item supports and one refutes (after stances are set)."""
    has_support = any((e.stance or STANCE_NEUTRAL) == STANCE_SUPPORTS for e in evidence)
    has_refute = any((e.stance or STANCE_NEUTRAL) == STANCE_REFUTES for e in evidence)
    return bool(has_support and has_refute)
