"""
Verdict aggregator: combine multiple sub-claim verification results into one verdict, reasoning, and citation list.
Used when a claim was decomposed into sub-claims; aggregation is deterministic (verdict) with optional LLM summarization (reasoning).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from openai import OpenAI

from backend.config import OPENAI_API_KEY, OPENAI_LLM_MODEL
from backend.constants import Verdict

logger = logging.getLogger(__name__)

# Max citations to return in aggregated response (dedupe by URL, then cap)
AGGREGATOR_MAX_CITATIONS: int = 25


def _aggregate_verdict_value(sub_results: List[Dict[str, Any]]) -> str:
    """
    Compute overall verdict from sub-results. Priority order:
    1. Any Refuted -> Refuted
    2. Any Mixed / Disputed -> Mixed / Disputed
    3. All Supported -> Supported
    4. All Not Enough Evidence or Unverifiable -> Not Enough Evidence
    5. Else -> Mixed / Disputed
    """
    if not sub_results:
        return Verdict.NOT_ENOUGH_EVIDENCE.value
    verdicts = [
        (r.get("verdict") or "").strip()
        for r in sub_results
        if isinstance(r.get("verdict"), str)
    ]
    if not verdicts:
        return Verdict.NOT_ENOUGH_EVIDENCE.value
    if any(v == Verdict.REFUTED.value for v in verdicts):
        return Verdict.REFUTED.value
    if any(v == Verdict.MIXED_DISPUTED.value for v in verdicts):
        return Verdict.MIXED_DISPUTED.value
    if all(v == Verdict.SUPPORTED.value for v in verdicts):
        return Verdict.SUPPORTED.value
    if all(
        v in (Verdict.NOT_ENOUGH_EVIDENCE.value, Verdict.UNVERIFIABLE.value)
        for v in verdicts
    ):
        return Verdict.NOT_ENOUGH_EVIDENCE.value
    return Verdict.MIXED_DISPUTED.value


def _merge_citations(sub_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge citation lists from sub-results, deduplicate by URL, cap at AGGREGATOR_MAX_CITATIONS."""
    seen_urls: set[str] = set()
    merged: List[Dict[str, Any]] = []
    for r in sub_results:
        citations = r.get("citations")
        if not isinstance(citations, list):
            continue
        for c in citations:
            if not isinstance(c, dict):
                continue
            url = (c.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append({
                "title": c.get("title") or "",
                "url": url,
                "snippet": c.get("snippet") or "",
            })
            if len(merged) >= AGGREGATOR_MAX_CITATIONS:
                return merged
    return merged


def _summarize_reasoning_llm(
    overall_verdict: str,
    sub_results: List[Dict[str, Any]],
) -> str:
    """Use LLM to summarize sub-result reasoning into 2-4 sentences. Fallback on concatenation."""
    if not OPENAI_API_KEY or not sub_results:
        return _reasoning_fallback(sub_results)
    parts = []
    for i, r in enumerate(sub_results, 1):
        v = r.get("verdict") or "N/A"
        reason = (r.get("reasoning") or "").strip() or "No reasoning provided."
        parts.append(f"Sub-claim {i} verdict: {v}. Reasoning: {reason[:300]}")
    prompt = f"""You are a fact-checking assistant. Below are the verification results for each sub-claim of a decomposed claim. Write a short, neutral summary (2-4 sentences) of the overall finding. Use only the information below; do not invent facts or sources.

Overall verdict for the combined claim: {overall_verdict}

Sub-results:
"""
    for p in parts:
        prompt += "\n- " + p + "\n"
    prompt += "\nSummary:"
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text if text else _reasoning_fallback(sub_results)
    except Exception as e:
        logger.warning("Aggregator reasoning summarization failed: %s", e)
        return _reasoning_fallback(sub_results)


def _reasoning_fallback(sub_results: List[Dict[str, Any]]) -> str:
    """Concatenate each sub-claim's reasoning with a short prefix."""
    if not sub_results:
        return "No sub-results to aggregate."
    parts = []
    for i, r in enumerate(sub_results, 1):
        reason = (r.get("reasoning") or "").strip() or "No reasoning provided."
        parts.append(f"Sub-claim {i}: {reason}")
    return " ".join(parts)


def aggregate_verdicts(
    sub_results: List[Dict[str, Any]],
    sub_claims: List[str] | None = None,
    use_llm_reasoning: bool = True,
) -> Dict[str, Any]:
    """
    Aggregate sub-claim verification results into one response.

    Each element of sub_results must have keys: verdict, reasoning, citations
    (same shape as single-claim API response). Optional key: claim (for sub_results in output).

    If sub_claims is provided and matches length of sub_results, each sub_result
    is augmented with the corresponding claim for the optional sub_results list.

    Returns dict with: verdict, reasoning, citations, and sub_results (when decomposed).
    """
    if not sub_results:
        return {
            "verdict": Verdict.NOT_ENOUGH_EVIDENCE.value,
            "reasoning": "No sub-results to aggregate.",
            "citations": [],
        }
    verdict = _aggregate_verdict_value(sub_results)
    citations = _merge_citations(sub_results)
    if use_llm_reasoning:
        reasoning = _summarize_reasoning_llm(verdict, sub_results)
    else:
        reasoning = _reasoning_fallback(sub_results)
    out: Dict[str, Any] = {
        "verdict": verdict,
        "reasoning": reasoning,
        "citations": citations,
    }
    # Attach sub_results for transparency (optionally include claim per item)
    augmented: List[Dict[str, Any]] = []
    for i, r in enumerate(sub_results):
        item = {
            "verdict": r.get("verdict") or Verdict.NOT_ENOUGH_EVIDENCE.value,
            "reasoning": (r.get("reasoning") or "").strip(),
            "citations": list(r.get("citations") or []),
        }
        if sub_claims and i < len(sub_claims):
            item["claim"] = sub_claims[i]
        elif r.get("claim") is not None:
            item["claim"] = r["claim"]
        augmented.append(item)
    out["sub_results"] = augmented
    return out
