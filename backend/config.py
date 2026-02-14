"""
Application configuration loaded from environment variables.
Configurable values live here; constants and enums live in constants.py.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_env(key: str, default: str | None = None) -> str | None:
    """Return env value or default; empty string treated as missing."""
    val = os.getenv(key)
    if val is not None and val.strip() == "":
        return default
    return val if val is not None else default


def _get_env_int(key: str, default: int) -> int:
    """Return env value as int or default."""
    val = _get_env(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


# API keys
OPENAI_API_KEY: str | None = _get_env("OPENAI_API_KEY")
SERP_API_KEY: str | None = _get_env("SERP_API_KEY")
SERP_API_BASE_URL: str = _get_env("SERP_API_BASE_URL") or "https://serpapi.com/search"

# Claim validation
CLAIM_MAX_LENGTH: int = _get_env_int("CLAIM_MAX_LENGTH", 2000)

# RAG
RAG_TOP_K: int = _get_env_int("RAG_TOP_K", 10)
RAG_EMBEDDING_MODEL: str = _get_env("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small"
CHROMA_PERSIST_DIR: str = _get_env("CHROMA_PERSIST_DIR") or str(
    Path(__file__).resolve().parent / "chroma_data"
)

# Agentic loop
AGENTIC_LOOP_MAX_ITER: int = _get_env_int("AGENTIC_LOOP_MAX_ITER", 3)

# LLM (verdict / stance / reasoning)
OPENAI_LLM_MODEL: str = _get_env("OPENAI_LLM_MODEL") or "gpt-4o-mini"

# Optional: min sources for Supported/Refuted (can override in constants)
MIN_SOURCES_FOR_VERDICT: int = _get_env_int("MIN_SOURCES_FOR_VERDICT", 1)

# SERP
SERP_NUM_RESULTS: int = _get_env_int("SERP_NUM_RESULTS", 10)
SERP_REQUEST_TIMEOUT_SEC: int = _get_env_int("SERP_REQUEST_TIMEOUT_SEC", 15)

# Reranker (cross-encoder on merged evidence)
RERANK_MODEL: str = _get_env("RERANK_MODEL") or "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_K: int = _get_env_int("RERANK_TOP_K", 25)

# Citation verification: credible domains (comma-separated); empty uses DEFAULT_CREDIBLE_DOMAINS
def _get_credible_domains() -> set[str]:
    from backend.constants import DEFAULT_CREDIBLE_DOMAINS

    raw = _get_env("CREDIBLE_DOMAINS")
    if raw is None or not raw.strip():
        return set(DEFAULT_CREDIBLE_DOMAINS)
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


CREDIBLE_DOMAINS: set[str] = _get_credible_domains()

# KB refresh job
REFRESH_QUERIES: str | None = _get_env("REFRESH_QUERIES")
REFRESH_NUM_RESULTS_PER_QUERY: int = _get_env_int("REFRESH_NUM_RESULTS_PER_QUERY", 10)
REFRESH_CHUNK_MAX_CHARS: int = _get_env_int("REFRESH_CHUNK_MAX_CHARS", 512)
REFRESH_CHUNK_OVERLAP: int = _get_env_int("REFRESH_CHUNK_OVERLAP", 100)
REFRESH_EMBED_BATCH_SIZE: int = _get_env_int("REFRESH_EMBED_BATCH_SIZE", 100)


def get_refresh_queries() -> list[str]:
    """Return query list for refresh job: REFRESH_QUERIES (comma-separated) or DEFAULT_CURRENT_AFFAIRS_QUERIES."""
    from backend.constants import DEFAULT_CURRENT_AFFAIRS_QUERIES

    raw = REFRESH_QUERIES
    if raw is None or not raw.strip():
        return list(DEFAULT_CURRENT_AFFAIRS_QUERIES)
    return [q.strip() for q in raw.split(",") if q.strip()]
