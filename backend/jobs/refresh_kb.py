"""
Knowledge base refresh job: fetch top current-affairs from SERP, chunk, embed, upsert into ChromaDB.
Designed to be run via cron every 24 hours (e.g. python -m backend.jobs.refresh_kb).
Uses diverse queries, credible-first ordering, sentence-aware chunking, stable IDs, batched embed, and safe swap.
"""

from __future__ import annotations

import hashlib
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from backend.config import (
    CREDIBLE_DOMAINS,
    get_refresh_queries,
    REFRESH_CHUNK_MAX_CHARS,
    REFRESH_CHUNK_OVERLAP,
    REFRESH_EMBED_BATCH_SIZE,
    REFRESH_NUM_RESULTS_PER_QUERY,
)
from backend.constants import COLLECTION_CURRENT_AFFAIRS_24H, REFRESH_TEMP_COLLECTION
from backend.services.embeddings import embed
from backend.services.serp_client import search
from backend.services.source_credibility import _domain_from_url
from backend.services.vector_store import (
    add_documents_with_embeddings,
    clone_collection,
    delete_collection,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _chunk_text(
    text: str,
    max_chars: int = REFRESH_CHUNK_MAX_CHARS,
    overlap: int = REFRESH_CHUNK_OVERLAP,
) -> List[str]:
    """
    Split text into chunks. Short content (<= max_chars) returns a single chunk.
    Long content is split at sentence boundaries (. ) where possible, with overlap.
    """
    if not text or max_chars < 1:
        return []
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            last_dot = text.rfind(". ", start, end + 1)
            if last_dot != -1:
                end = last_dot + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if overlap < (end - start) else end
        if start >= len(text):
            break
    return chunks


def _gather_serp_results(
    queries: List[str],
    num_per_query: int,
    credible_domains: set[str],
) -> List[Tuple[str, str, str]]:
    """
    Run SERP for each query; return list of (url, title, snippet) with credible-first ordering and dedupe.
    """
    credible_list: List[Tuple[str, str, str]] = []
    other_list: List[Tuple[str, str, str]] = []
    for q in queries:
        try:
            results = search(query=q, num_results=num_per_query)
            for r in results:
                url = (r.get("url") or "").strip()
                if not url:
                    continue
                title = (r.get("title") or "").strip()
                snippet = (r.get("snippet") or "").strip()
                domain = _domain_from_url(url)
                entry = (url, title, snippet)
                if domain and domain in credible_domains:
                    credible_list.append(entry)
                else:
                    other_list.append(entry)
        except Exception as e:
            logger.warning("SERP failed for query %s: %s", q, e)
            continue

    seen_urls: set[str] = set()
    ordered: List[Tuple[str, str, str]] = []
    for url, title, snippet in credible_list + other_list:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        ordered.append((url, title, snippet))
    return ordered


def run_refresh() -> int:
    """
    Fetch SERP results for current-affairs queries (credible-first), chunk, embed in batches,
    write to temp collection, then clone to live. Returns number of chunks stored.
    """
    now = datetime.now(timezone.utc).isoformat()[:10]
    queries = get_refresh_queries()
    num_per_query = REFRESH_NUM_RESULTS_PER_QUERY
    credible_domains = CREDIBLE_DOMAINS

    ordered = _gather_serp_results(queries, num_per_query, credible_domains)
    if not ordered:
        logger.warning("No SERP results; skipping refresh.")
        return 0

    all_docs: List[Dict[str, Any]] = []
    for url, title, snippet in ordered:
        content = f"{title}\n\n{snippet}"
        chunks = _chunk_text(content)
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        for i, ch in enumerate(chunks):
            all_docs.append(
                {
                    "id": f"ca_{url_hash}_{i}",
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

    if not all_docs:
        logger.warning("No documents to add; skipping refresh.")
        return 0

    delete_collection(REFRESH_TEMP_COLLECTION)

    ids = [d["id"] for d in all_docs]
    documents = [d["content"] for d in all_docs]
    metadatas = [d["metadata"] for d in all_docs]
    batch_size = REFRESH_EMBED_BATCH_SIZE
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_docs = documents[i : i + batch_size]
        batch_metas = metadatas[i : i + batch_size]
        try:
            embeddings_batch = embed(batch_docs)
            add_documents_with_embeddings(
                REFRESH_TEMP_COLLECTION,
                batch_ids,
                batch_docs,
                batch_metas,
                embeddings_batch,
            )
        except Exception as e:
            logger.exception("Batch embed/add failed at offset %s: %s", i, e)
            raise

    clone_collection(REFRESH_TEMP_COLLECTION, COLLECTION_CURRENT_AFFAIRS_24H)
    logger.info("Refresh complete: %s chunks in %s", len(all_docs), COLLECTION_CURRENT_AFFAIRS_24H)
    return len(all_docs)


if __name__ == "__main__":
    try:
        n = run_refresh()
        sys.exit(0 if n >= 0 else 1)
    except Exception as e:
        logger.exception("Refresh job failed: %s", e)
        sys.exit(1)
