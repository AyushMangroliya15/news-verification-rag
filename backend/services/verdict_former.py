"""
Verdict formation: from evidence and evaluator state produce verdict, reasoning, citations.
Uses LLM for reasoning; then runs validation rules.
"""

import logging
from typing import List

from openai import OpenAI

from backend.config import CREDIBLE_DOMAINS, OPENAI_API_KEY, OPENAI_LLM_MODEL
from backend.constants import (
    STANCE_NEUTRAL,
    STANCE_REFUTES,
    STANCE_SUPPORTS,
    Verdict,
)
from backend.models import Citation, EvidenceItem
from backend.services.source_credibility import filter_credible_citations
from backend.services.validation_rules import apply_validation_rules

logger = logging.getLogger(__name__)


def _decide_verdict(
    evidence: List[EvidenceItem],
    sufficient: bool,
    has_conflict: bool,
) -> str:
    """Decide verdict from state (no LLM)."""
    if not evidence or not sufficient:
        return Verdict.NOT_ENOUGH_EVIDENCE.value
    if has_conflict:
        return Verdict.MIXED_DISPUTED.value
    stances = [e.stance or STANCE_NEUTRAL for e in evidence]
    if any(s == STANCE_SUPPORTS for s in stances) and not any(s == STANCE_REFUTES for s in stances):
        return Verdict.SUPPORTED.value
    if any(s == STANCE_REFUTES for s in stances) and not any(s == STANCE_SUPPORTS for s in stances):
        return Verdict.REFUTED.value
    return Verdict.NOT_ENOUGH_EVIDENCE.value


def _evidence_to_citations(evidence: List[EvidenceItem]) -> List[Citation]:
    """Convert evidence items to citation list (for response)."""
    return [
        Citation(title=e.title, url=e.url, snippet=e.snippet or e.title)
        for e in evidence
    ]


def _generate_reasoning(claim: str, verdict: str, evidence: List[EvidenceItem]) -> str:
    """Use LLM to generate short reasoning given claim, verdict, and evidence."""
    if not OPENAI_API_KEY or not evidence:
        return "Evidence was evaluated against the claim; see citations for sources."
    summary = "\n".join(
        f"- [{e.title}]({e.url}): {e.snippet[:200]}..." if len(e.snippet or "") > 200 else f"- [{e.title}]({e.url}): {e.snippet or ''}"
        for e in evidence[:10]
    )
    prompt = f"""You are a fact-checking assistant. Write a short, neutral reasoning (2-4 sentences) for the following verification result. Do not invent sources; only refer to the evidence listed. Do not use markdown links in the body.

Claim: {claim[:400]}
Verdict: {verdict}

Evidence (title, url, snippet):
{summary}

Reasoning:"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text if text else "Evidence was evaluated; see citations."
    except Exception as e:
        logger.warning("Reasoning generation failed: %s", e)
        return "Evidence was evaluated against the claim; see citations for sources."


def form_verdict(
    claim: str,
    evidence: List[EvidenceItem],
    sufficient: bool,
    has_conflict: bool,
) -> tuple[str, str, List[Citation]]:
    """
    Produce final verdict, reasoning, and citations. Applies validation rules.
    Returns (verdict, reasoning, citations) for API response.
    """
    verdict = _decide_verdict(evidence, sufficient, has_conflict)
    citations = _evidence_to_citations(evidence)
    credible_citations = filter_credible_citations(citations, CREDIBLE_DOMAINS)
    # If no citations pass credibility filter, or if too few pass (< 3 or < 30% of total),
    # fall back to showing all (avoid losing too many citations when we have evidence)
    if not credible_citations:
        citations = citations
    elif len(credible_citations) < 3 and len(credible_citations) < len(citations) * 0.3:
        # Too few credible citations relative to total - use all to preserve evidence diversity
        logger.info(
            "Credibility filter too restrictive: %d credible out of %d total citations, using all",
            len(credible_citations),
            len(citations),
        )
        citations = citations
    else:
        citations = credible_citations
    reasoning = _generate_reasoning(claim, verdict, evidence)
    allowed_urls = {e.url for e in evidence}
    verdict, reasoning, citations = apply_validation_rules(
        verdict, reasoning, citations, allowed_urls
    )
    return verdict, reasoning, citations
