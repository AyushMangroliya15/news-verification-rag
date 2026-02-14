"""
RAG Agent: retrieve evidence from ChromaDB using OpenAI embeddings.
Returns list of EvidenceItem; supports current-affairs-only or both collections.
"""

import logging
from typing import List

from backend.constants import COLLECTION_CURRENT_AFFAIRS_24H, COLLECTION_STATIC_GK
from backend.models import EvidenceItem
from backend.services.embeddings import embed
from backend.services.vector_store import query

logger = logging.getLogger(__name__)


def retrieve(
    claim: str,
    top_k: int,
    use_current_affairs_only: bool = False,
) -> List[EvidenceItem]:
    """
    Retrieve evidence from Vector DB for the given claim.
    Deduplicates by URL. Returns empty list if collection is empty or on error.
    """
    if not claim.strip():
        return []
    try:
        query_embeddings = embed(claim)
        if not query_embeddings:
            return []
        query_embedding = query_embeddings[0]
    except Exception as e:
        logger.warning("RAG embed failed for claim: %s", e)
        return []

    collections = [COLLECTION_CURRENT_AFFAIRS_24H]
    if not use_current_affairs_only:
        collections.append(COLLECTION_STATIC_GK)

    seen_urls: set[str] = set()
    items: List[EvidenceItem] = []

    for coll_name in collections:
        try:
            results = query(
                collection_name=coll_name,
                query_embedding=query_embedding,
                top_k=top_k,
                filter_metadata=None,
            )
            for r in results:
                meta = r.get("metadata") or {}
                url = (meta.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                items.append(
                    EvidenceItem(
                        title=(meta.get("title") or "")[:500],
                        url=url,
                        snippet=(meta.get("snippet") or r.get("content") or "")[:1000],
                        source=meta.get("source") or "rag",
                        score=float(r.get("score") or 0.0),
                    )
                )
        except Exception as e:
            logger.warning("RAG query failed for collection %s: %s", coll_name, e)
            continue

    return items
