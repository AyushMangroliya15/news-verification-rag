"""
Constants, enums, and fixed values for the verification pipeline.
Business logic uses these; configurable env values are in config.py.
"""
from __future__ import annotations

from enum import Enum


class Verdict(str, Enum):
    """Allowed verdict values for claim verification."""

    SUPPORTED = "Supported"
    REFUTED = "Refuted"
    NOT_ENOUGH_EVIDENCE = "Not Enough Evidence"
    MIXED_DISPUTED = "Mixed / Disputed"
    UNVERIFIABLE = "Unverifiable"


# Minimum number of cited sources to allow Supported/Refuted (validation rule)
MIN_EVIDENCE_COUNT: int = 1

# Vector DB collection names
COLLECTION_CURRENT_AFFAIRS_24H: str = "current_affairs_24h"
COLLECTION_STATIC_GK: str = "static_gk"

# Stance classification for evidence items
STANCE_SUPPORTS: str = "supports"
STANCE_REFUTES: str = "refutes"
STANCE_NEUTRAL: str = "neutral"

# Default credible domains for citation verification (news and fact-checkers)
DEFAULT_CREDIBLE_DOMAINS: list[str] = [
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "bbc.co.uk",
    "nytimes.com",
    "theguardian.com",
    "washingtonpost.com",
    "npr.org",
    "factcheck.org",
    "snopes.com",
    "politifact.com",
    "afp.com",
    "usatoday.com",
    "cbsnews.com",
    "nbcnews.com",
    "abcnews.go.com",
    "poynter.org",
]

# KB refresh: default SERP queries for current-affairs (diverse topics)
DEFAULT_CURRENT_AFFAIRS_QUERIES: list[str] = [
    "today's top news",
    "breaking news today",
    "current affairs today",
    "headlines today",
    "world news today",
    "politics news today",
    "technology news today",
    "science news today",
    "health news today",
    "business news today",
    "sports news today",
    "climate environment news today",
    "economy news today",
    "fact check viral claim",
    "debunked news today",
    "misinformation fact check",
    "US news today",
    "international news today",
]

# Temp collection name for safe refresh (build here then clone to live)
REFRESH_TEMP_COLLECTION: str = "current_affairs_24h_new"
