"""
Reranker: cross-encoder reranking of merged evidence by relevance to the claim.
Lazy-loads the model; on failure returns the original list so the pipeline continues.
"""

from __future__ import annotations

import logging
from typing import List

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


def rerank(
    claim: str,
    items: List[EvidenceItem],
    top_k: int,
    model_name: str | None = None,
) -> List[EvidenceItem]:
    """
    Rerank evidence items by relevance to the claim using a cross-encoder.
    Returns top_k items sorted by score descending. Preserves all EvidenceItem fields;
    updates score to the reranker score. On empty items or failure returns original list.
    """
    if not claim or not items:
        return items

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
        scores = model.predict(pairs)
        # scores is typically a 1d array; ensure we can index by position
        if hasattr(scores, "tolist"):
            scores = scores.tolist()
        elif hasattr(scores, "__iter__") and not isinstance(scores, list):
            scores = list(scores)
    except Exception as e:
        logger.warning("Reranker predict failed: %s; returning evidence unchanged.", e)
        return items

    if len(scores) != len(items):
        logger.warning(
            "Reranker score length %s != items length %s; returning evidence unchanged.",
            len(scores),
            len(items),
        )
        return items

    # Sort by score descending and take top_k; preserve EvidenceItem, set score
    indexed = list(zip(scores, items))
    indexed.sort(key=lambda x: x[0], reverse=True)
    top = indexed[:top_k]
    result: List[EvidenceItem] = []
    for score, item in top:
        result.append(
            EvidenceItem(
                title=item.title,
                url=item.url,
                snippet=item.snippet,
                source=item.source,
                score=float(score),
                stance=item.stance,
            )
        )
    return result
