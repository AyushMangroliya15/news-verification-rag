"""
Knowledge base refresh job: fetch top current-affairs from SERP, chunk, embed, upsert into ChromaDB.
Designed to be run via cron every 24 hours (e.g. python -m backend.jobs.refresh_kb).
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.constants import COLLECTION_CURRENT_AFFAIRS_24H
from backend.services.serp_client import search
from backend.services.vector_store import add_documents, delete_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Queries used to populate "top current affairs" (last 24h)
CURRENT_AFFAIRS_QUERIES: List[str] = [
    "today's top news",
    "breaking news today",
    "current affairs today",
]

CHUNK_MAX_CHARS = 512
CHUNK_OVERLAP = 100


def _chunk_text(text: str, max_chars: int = CHUNK_MAX_CHARS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks by character count."""
    if not text or max_chars < 1:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap if overlap < max_chars else end
    return chunks


def run_refresh() -> int:
    """
    Fetch SERP results for current-affairs queries, chunk, embed, store in ChromaDB.
    Replaces the current_affairs_24h collection. Returns number of chunks stored.
    """
    now = datetime.now(timezone.utc).isoformat()[:10]
    all_docs: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()

    for q in CURRENT_AFFAIRS_QUERIES:
        try:
            results = search(query=q, num_results=10)
            for r in results:
                url = (r.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                title = (r.get("title") or "").strip()
                snippet = (r.get("snippet") or "").strip()
                content = f"{title}\n\n{snippet}"
                chunks = _chunk_text(content)
                for i, ch in enumerate(chunks):
                    all_docs.append(
                        {
                            "content": ch,
                            "metadata": {
                                "url": url,
                                "title": title[:500],
                                "snippet": snippet[:1000],
                                "date": now,
                                "source": "serp",
                            },
                        }
                    )
        except Exception as e:
            logger.warning("SERP failed for query %s: %s", q, e)
            continue

    if not all_docs:
        logger.warning("No documents to add; skipping refresh.")
        return 0

    delete_collection(COLLECTION_CURRENT_AFFAIRS_24H)
    ids = [f"ca_{i}" for i in range(len(all_docs))]
    documents = [d["content"] for d in all_docs]
    metadatas = [d["metadata"] for d in all_docs]
    add_documents(COLLECTION_CURRENT_AFFAIRS_24H, ids, documents, metadatas)
    logger.info("Refresh complete: %s chunks in %s", len(all_docs), COLLECTION_CURRENT_AFFAIRS_24H)
    return len(all_docs)


if __name__ == "__main__":
    try:
        n = run_refresh()
        sys.exit(0 if n >= 0 else 1)
    except Exception as e:
        logger.exception("Refresh job failed: %s", e)
        sys.exit(1)
