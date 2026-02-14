"""
Constants, enums, and fixed values for the verification pipeline.
Business logic uses these; configurable env values are in config.py.
"""

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
