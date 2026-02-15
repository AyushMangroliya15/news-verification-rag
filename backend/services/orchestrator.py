"""
Orchestrator: run full verification pipeline with agentic loop.
Gathers evidence from WEB + RAG, evaluates, refines up to max iterations, then forms verdict.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from backend.config import AGENTIC_LOOP_MAX_ITER, RAG_TOP_K, RERANK_TOP_K
from backend.models import Citation, EvidenceItem
from backend.services.evidence_evaluator import (
    attach_stances,
    has_conflict,
    is_sufficient,
)
from backend.services.rag_agent import retrieve as rag_retrieve
from backend.services.reranker import rerank as rerank_evidence
from backend.services.verdict_former import form_verdict
from backend.services.web_agent import fetch_evidence as web_fetch_evidence

logger = logging.getLogger(__name__)


def _merge_and_dedupe(web_items: List[EvidenceItem], rag_items: List[EvidenceItem]) -> List[EvidenceItem]:
    """
    Merge evidence from WEB (Tavily) and RAG, deduplicate by URL, and filter homepage URLs.
    Tavily returns article URLs by default, so we only filter RAG results for homepages.
    """
    from backend.services.url_utils import _is_homepage_url
    
    seen: set[str] = set()
    out: List[EvidenceItem] = []
    
    logger.info("Merging evidence: %d Tavily items, %d RAG items", len(web_items), len(rag_items))
    
    # Log sources for debugging
    tavily_urls = [item.url for item in web_items]
    rag_urls = [item.url for item in rag_items]
    logger.info("Tavily URLs: %s", tavily_urls[:5])  # First 5
    logger.info("RAG URLs: %s", rag_urls[:5])  # First 5
    
    for item in web_items + rag_items:
        url = (item.url or "").strip()
        if not url or url in seen:
            continue
        
        # Filter homepage URLs only for RAG results (Tavily returns article URLs by default)
        if item.source == "rag" and _is_homepage_url(url):
            logger.warning("Filtered homepage URL from RAG evidence: %s (source: %s)", url, item.source)
            continue
        
        # Also check if it's a homepage regardless of source (safety check)
        if _is_homepage_url(url):
            logger.warning("Filtered homepage URL (unexpected source '%s'): %s", item.source, url)
            continue
        
        seen.add(url)
        out.append(item)
        logger.debug("Added evidence item: %s (source: %s)", url, item.source)
    
    logger.info("After merge and dedupe: %d total evidence items", len(out))
    return out


def run_verification(claim: str, claim_id: str | None = None) -> Dict[str, Any]:
    """
    Run the full verification pipeline. Returns dict with keys:
    verdict (str), reasoning (str), citations (list of {title, url, snippet}).
    On failure returns Not Enough Evidence with safe reasoning.
    """
    claim = (claim or "").strip()
    if not claim:
        return {
            "verdict": "Not Enough Evidence",
            "reasoning": "No claim provided.",
            "citations": [],
        }

    evidence: List[EvidenceItem] = []
    sufficient = False
    conflict = False
    top_k = RAG_TOP_K
    use_current_only = False

    try:
        for iteration in range(AGENTIC_LOOP_MAX_ITER):
            # Gather evidence
            web_items: List[EvidenceItem] = []
            try:
                web_items = web_fetch_evidence(claim, num_per_query=5)
            except Exception as e:
                logger.warning("WEB agent failed: %s", e)

            rag_items: List[EvidenceItem] = []
            try:
                rag_items = rag_retrieve(claim, top_k=top_k, use_current_affairs_only=use_current_only)
            except Exception as e:
                logger.warning("RAG agent failed: %s", e)

            evidence = _merge_and_dedupe(web_items, rag_items)
            if not evidence:
                if iteration < AGENTIC_LOOP_MAX_ITER - 1:
                    top_k = min(top_k + 5, 20)
                    use_current_only = True
                continue

            try:
                # Reranker now filters homepages before reranking and uses hybrid scoring
                evidence = rerank_evidence(claim, evidence, top_k=RERANK_TOP_K)
                logger.info("After reranking: %d evidence items", len(evidence))
            except Exception as e:
                logger.warning("Reranker failed: %s; using evidence unchanged.", e)

            attach_stances(claim, evidence)
            sufficient = is_sufficient(evidence)
            conflict = has_conflict(evidence, claim)

            if sufficient and not conflict:
                break
            # Refine: next iteration use higher top_k or current-affairs only
            top_k = min(top_k + 5, 20)
            if iteration + 1 < AGENTIC_LOOP_MAX_ITER:
                use_current_only = True

        verdict, reasoning, citations = form_verdict(claim, evidence, sufficient, conflict)
        out: Dict[str, Any] = {
            "verdict": verdict,
            "reasoning": reasoning,
            "citations": [{"title": c.title, "url": c.url, "snippet": c.snippet} for c in citations],
        }
        # Flag for HITL when result is ambiguous (conflict or insufficient after max iter)
        if claim_id and (not sufficient or conflict):
            out["requires_review"] = True
            out["claim_id"] = claim_id
        return out
    except Exception as e:
        logger.exception("Verification pipeline failed: %s", e)
        return {
            "verdict": "Not Enough Evidence",
            "reasoning": "Verification could not be completed. Please try again.",
            "citations": [],
        }
