"""
Claim decomposer: split a long or complex claim into sub-claims for separate verification.
Returns a list of sub-claim strings; if decomposition is skipped or fails, returns [claim].
"""
from __future__ import annotations

import json
import logging
import re
from typing import List

from openai import OpenAI

from backend.config import (
    DECOMPOSE_ENABLED,
    DECOMPOSE_MAX_SUBCLAIMS,
    DECOMPOSE_MIN_CLAIM_LENGTH,
    DECOMPOSE_USE_LLM,
    OPENAI_API_KEY,
    OPENAI_LLM_MODEL,
)

logger = logging.getLogger(__name__)

# Max claim length to send to LLM (keep within context)
_DECOMPOSE_CLAIM_TRUNCATE_CHARS: int = 800


def _extract_json_string_array(text: str) -> List[str] | None:
    """
    Extract a JSON array of strings from LLM response.
    Handles raw '[...]' or markdown-wrapped (e.g. ```json\\n[...]```).
    Returns list of non-empty stripped strings, or None if parsing fails.
    """
    if not text or not text.strip():
        return None
    s = text.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if len(lines) > 1:
            rest = "\n".join(lines[1:])
            if rest.endswith("```"):
                rest = rest[:-3].strip()
            s = rest
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
                    if not isinstance(arr, list):
                        return None
                    out: List[str] = []
                    for item in arr:
                        if isinstance(item, str) and item.strip():
                            out.append(item.strip())
                    return out if out else None
                except (json.JSONDecodeError, TypeError):
                    pass
                return None
    return None


def _decompose_by_llm(claim: str) -> List[str]:
    """Call LLM to split claim into distinct factual sub-claims. Returns list or empty on failure."""
    if not OPENAI_API_KEY:
        logger.warning("Claim decomposer: OPENAI_API_KEY not set; skipping LLM decomposition.")
        return []
    claim_truncated = claim[:_DECOMPOSE_CLAIM_TRUNCATE_CHARS]
    if len(claim) > _DECOMPOSE_CLAIM_TRUNCATE_CHARS:
        claim_truncated = claim_truncated.rsplit(" ", 1)[0] if " " in claim_truncated else claim_truncated
    prompt = f"""You are a fact-checking assistant. The following text may contain one or more distinct factual claims that can be verified independently.

Your task: list ONLY the distinct factual claims. Output a JSON array of strings, one claim per element. Use the exact wording of each claim. If there is only one factual claim, return that single claim as a one-element array. Do not add commentary or explanation outside the JSON array.

Text:
{claim_truncated}

Output (JSON array of strings only):"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        text = (resp.choices[0].message.content or "").strip()
        arr = _extract_json_string_array(text)
        if not arr:
            return []
        return arr[:DECOMPOSE_MAX_SUBCLAIMS]
    except Exception as e:
        logger.warning("Claim decomposer LLM call failed: %s", e)
        return []


def _decompose_by_rules(claim: str) -> List[str]:
    """Fallback: split on sentence boundaries or conjunctions when LLM is disabled."""
    # Split on sentence boundaries (period + space) or " and " / ", "
    parts = re.split(r"\.\s+|\s+and\s+|\s*,\s*", claim, maxsplit=DECOMPOSE_MAX_SUBCLAIMS - 1)
    out: List[str] = []
    for p in parts:
        p = p.strip()
        if p and len(p) >= 10:  # skip tiny fragments
            out.append(p)
    if len(out) <= 1:
        return []
    return out[:DECOMPOSE_MAX_SUBCLAIMS]


def decompose_claim(claim: str) -> List[str]:
    """
    Decompose a claim into sub-claims for separate verification (LLM-based when DECOMPOSE_USE_LLM is true).

    We only skip the LLM when decomposition is disabled, claim is empty, or claim length is below
    DECOMPOSE_MIN_CLAIM_LENGTH (small threshold to avoid calling the LLM for trivial one-word input).

    Returns [claim] (single element) when:
    - decomposition is disabled,
    - claim length is below DECOMPOSE_MIN_CLAIM_LENGTH,
    - LLM (or rules) returns 0 or 1 sub-claim (or parsing fails),
    - or any exception occurs.

    Otherwise returns a list of sub-claim strings, capped at DECOMPOSE_MAX_SUBCLAIMS.
    """
    if not claim or not claim.strip():
        return [claim] if claim is not None else [""]
    claim = claim.strip()
    if not DECOMPOSE_ENABLED:
        return [claim]
    if len(claim) < DECOMPOSE_MIN_CLAIM_LENGTH:
        return [claim]
    sub_claims: List[str] = []
    if DECOMPOSE_USE_LLM:
        sub_claims = _decompose_by_llm(claim)
    else:
        sub_claims = _decompose_by_rules(claim)
    if not sub_claims or len(sub_claims) == 1:
        return [claim]
    logger.info("Claim decomposed into %d sub-claims", len(sub_claims))
    return sub_claims
