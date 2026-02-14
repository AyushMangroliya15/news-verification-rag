"""
Claim intake: normalize and validate user-provided claim text.
All verification flows start from a normalized, validated claim.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Tuple

from backend.config import CLAIM_MAX_LENGTH


def normalize(claim: str) -> str:
    """
    Normalize claim text: strip, collapse whitespace, optional unicode normalize.
    """
    if not claim:
        return ""
    text = unicodedata.normalize("NFKC", claim.strip())
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def validate(claim: str) -> Tuple[bool, str | None]:
    """
    Validate claim length and non-empty. Uses CLAIM_MAX_LENGTH from config.
    Returns (ok, error_message). error_message is None when ok is True.
    """
    normalized = normalize(claim)
    if not normalized:
        return False, "Claim cannot be empty."
    if len(normalized) > CLAIM_MAX_LENGTH:
        return False, f"Claim exceeds maximum length of {CLAIM_MAX_LENGTH} characters."
    return True, None
