"""
Reranker: cross-encoder reranking of merged evidence by relevance to the claim.
Uses hybrid scoring: semantic relevance + URL quality + source preference.
Lazy-loads the model; on failure returns the original list so the pipeline continues.
"""

from __future__ import annotations

import logging
from typing import List
from urllib.parse import urlparse

from backend.models import EvidenceItem

logger = logging.getLogger(__name__)

# Lazy-loaded CrossEncoder singleton
_cross_encoder = None


def _get_model(model_name: str):
    """Load CrossEncoder on first use."""
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder

            _cross_encoder = CrossEncoder(model_name)
        except Exception as e:
            logger.exception("Failed to load reranker model %s: %s", model_name, e)
            raise
    return _cross_encoder


def _url_quality_score(url: str) -> float:
    """
    Calculate URL quality score (0.0 to 1.0).
    Higher score = better quality (article-specific URLs).
    Lower score = category/homepage URLs.
    """
    if not url:
        return 0.0
    
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").strip()
        path_segments = [s for s in path.split("/") if s]
        
        # Empty path or just "/" = homepage (lowest quality)
        if not path or path == "/":
            return 0.0
        
        # More path segments = more specific (higher quality)
        # Article URLs typically have 2+ meaningful segments
        if len(path_segments) >= 3:
            return 1.0  # Very specific article URL
        elif len(path_segments) == 2:
            # Check if second segment looks like an article ID
            second = path_segments[1].lower()
            if (second.replace("-", "").replace("_", "").isalnum() and 
                len(second) > 5 and
                not second in {"news", "articles", "stories", "posts"}):
                return 0.9  # Likely article with ID
            else:
                return 0.3  # Category page
        elif len(path_segments) == 1:
            segment = path_segments[0].lower()
            # Category pages (low quality)
            category_patterns = {
                "news", "sports", "sport", "athletic", "athletics",
                "technology", "tech", "politics", "business", "health"
            }
            if segment in category_patterns or path.endswith("/"):
                return 0.2  # Category page
            else:
                return 0.6  # Might be an article, but uncertain
        
        return 0.5  # Default moderate quality
    except Exception:
        return 0.5  # Conservative default


def _source_preference_score(source: str) -> float:
    """
    Calculate source preference score.
    Tavily results are preferred over RAG (which may contain old/homepage URLs).
    """
    if source == "tavily":
        return 1.0
    elif source == "rag":
        return 0.7  # Slight penalty for RAG (may contain legacy data)
    else:
        return 0.8  # Unknown source


def rerank(
    claim: str,
    items: List[EvidenceItem],
    top_k: int,
    model_name: str | None = None,
) -> List[EvidenceItem]:
    """
    Rerank evidence items using hybrid scoring:
    1. Semantic relevance (cross-encoder)
    2. URL quality (article-specific vs homepage)
    3. Source preference (Tavily > RAG)
    
    Returns top_k items sorted by combined score descending.
    """
    if not claim or not items:
        return items

    # Filter homepages BEFORE reranking to avoid wasting compute on low-quality items
    from backend.services.url_utils import _is_homepage_url
    
    filtered_items = [item for item in items if not _is_homepage_url(item.url)]
    if len(filtered_items) < len(items):
        logger.info("Reranker: Filtered %d homepage URLs before reranking", len(items) - len(filtered_items))
        items = filtered_items
    
    if not items:
        return []

    if model_name is None:
        from backend.config import RERANK_MODEL
        model_name = RERANK_MODEL

    try:
        model = _get_model(model_name)
    except Exception:
        logger.warning("Reranker unavailable; returning evidence unchanged.")
        return items

    # Build (claim, doc) pairs: doc = title + snippet to stay within context limits
    max_doc_chars = 512
    pairs: List[List[str]] = []
    for item in items:
        doc = f"{item.title or ''}\n{item.snippet or ''}".strip()
        if len(doc) > max_doc_chars:
            doc = doc[: max_doc_chars - 3] + "..."
        pairs.append([claim, doc or "(no content)"])

    try:
        relevance_scores = model.predict(pairs)
        # scores is typically a 1d array; ensure we can index by position
        if hasattr(relevance_scores, "tolist"):
            relevance_scores = relevance_scores.tolist()
        elif hasattr(relevance_scores, "__iter__") and not isinstance(relevance_scores, list):
            relevance_scores = list(relevance_scores)
    except Exception as e:
        logger.warning("Reranker predict failed: %s; returning evidence unchanged.", e)
        return items

    if len(relevance_scores) != len(items):
        logger.warning(
            "Reranker score length %s != items length %s; returning evidence unchanged.",
            len(relevance_scores),
            len(items),
        )
        return items

    # Calculate hybrid scores: relevance + URL quality + source preference
    # Normalize relevance scores to 0-1 range (assuming they're typically -5 to 5)
    min_rel = min(relevance_scores) if relevance_scores else 0
    max_rel = max(relevance_scores) if relevance_scores else 1
    rel_range = max_rel - min_rel if max_rel != min_rel else 1
    
    hybrid_scores = []
    for i, item in enumerate(items):
        # Normalize relevance score to 0-1
        norm_relevance = (relevance_scores[i] - min_rel) / rel_range if rel_range > 0 else 0.5
        
        # Get quality signals
        url_quality = _url_quality_score(item.url)
        source_pref = _source_preference_score(item.source)
        
        # Hybrid score: weighted combination
        # 70% relevance, 20% URL quality, 10% source preference
        hybrid_score = (
            0.7 * norm_relevance +
            0.2 * url_quality +
            0.1 * source_pref
        )
        
        hybrid_scores.append((hybrid_score, relevance_scores[i], url_quality, source_pref, item))
    
    # Sort by hybrid score descending
    hybrid_scores.sort(key=lambda x: x[0], reverse=True)
    
    # Apply diversity: avoid too many results from same domain
    # Take top results but limit to 2 per domain for better diversity
    result: List[EvidenceItem] = []
    domain_count: dict[str, int] = {}
    max_per_domain = 2
    
    for hybrid_score, relevance_score, url_q, src_pref, item in hybrid_scores:
        if len(result) >= top_k:
            break
        
        # Extract domain
        try:
            parsed = urlparse(item.url)
            domain = (parsed.netloc or "").lower().replace("www.", "")
        except Exception:
            domain = ""
        
        # Check domain limit
        if domain and domain_count.get(domain, 0) >= max_per_domain:
            logger.debug("Skipping %s (domain %s already has %d results)", item.url, domain, max_per_domain)
            continue
        
        domain_count[domain] = domain_count.get(domain, 0) + 1
        result.append(
            EvidenceItem(
                title=item.title,
                url=item.url,
                snippet=item.snippet,
                source=item.source,
                score=float(hybrid_score),  # Store hybrid score
                stance=item.stance,
            )
        )
    
    logger.info("Reranker: Processed %d items, selected top %d (with diversity)", len(items), len(result))
    logger.info("Reranker top %d results (hybrid_score, relevance, url_quality, source, URL):", len(result))
    for idx, item in enumerate(result[:10], 1):
        # Find the score info for logging
        for hybrid, rel, url_q, src_pref, orig_item in hybrid_scores:
            if orig_item.url == item.url:
                logger.info(
                    "  %d. Hybrid=%.3f (Rel=%.3f, URL=%.2f, Src=%.2f) | %s | %s",
                    idx, hybrid, rel, url_q, src_pref, item.url, (item.title or "")[:50]
                )
                break
    
    return result
