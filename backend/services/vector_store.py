"""
ChromaDB vector store: query by embedding, return docs with content and metadata.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings

from backend.config import CHROMA_PERSIST_DIR
from backend.services.embeddings import embed

logger = logging.getLogger(__name__)

# Lazy singleton client
_client: chromadb.PersistentClient | None = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def query(
    collection_name: str,
    query_embedding: List[float],
    top_k: int,
    filter_metadata: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    Query a collection by embedding. Returns list of dicts with 'content' and 'metadata'.
    metadata should include url, title, snippet, date, source when available.
    """
    try:
        client = _get_client()
        coll = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        n_results = min(top_k, coll.count() or 1)
        if n_results < 1:
            return []
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if filter_metadata:
            kwargs["where"] = filter_metadata
        result = coll.query(**kwargs)
        documents = result.get("documents") or [[]]
        metadatas = result.get("metadatas") or [[]]
        distances = result.get("distances") or [[]]
        out: List[Dict[str, Any]] = []
        for i, doc in enumerate(documents[0] or []):
            meta = (metadatas[0] or [{}])[i] if i < len(metadatas[0] or []) else {}
            dist = (distances[0] or [0.0])[i] if i < len(distances[0] or []) else 0.0
            # Convert distance to a simple score (Chroma cosine distance: 0 = identical)
            score = 1.0 - (dist / 2.0) if dist is not None else 0.0
            out.append(
                {
                    "content": doc,
                    "metadata": meta,
                    "score": score,
                }
            )
        return out
    except Exception as e:
        logger.exception("Vector store query failed: %s", e)
        raise


def add_documents(
    collection_name: str,
    ids: List[str],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
) -> None:
    """
    Add documents to a collection. Embeds via OpenAI; Chroma stores by id.
    ids, documents, metadatas must be same length. Chroma metadata values must be str, int, float, or bool.
    """
    if not ids or not documents or len(ids) != len(documents) or len(documents) != len(metadatas):
        raise ValueError("ids, documents, metadatas must be same non-empty length.")
    embeddings_list = embed(documents)
    client = _get_client()
    coll = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    # Chroma expects metadatas with simple types
    clean_meta: List[Dict[str, Any]] = []
    for m in metadatas:
        clean_meta.append({k: (v if isinstance(v, (str, int, float, bool)) else str(v)) for k, v in (m or {}).items()})
    coll.add(ids=ids, documents=documents, metadatas=clean_meta, embeddings=embeddings_list)


def delete_collection(collection_name: str) -> None:
    """Delete a collection by name (e.g. to replace with fresh data)."""
    client = _get_client()
    try:
        client.delete_collection(name=collection_name)
    except Exception as e:
        logger.warning("delete_collection %s: %s", collection_name, e)
