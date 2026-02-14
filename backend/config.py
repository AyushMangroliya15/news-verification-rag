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
