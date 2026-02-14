"""
Shared data models for the verification pipeline.
Used by RAG, SERP, evidence evaluator, and API response.
"""

from dataclasses import dataclass
from typing import Literal, Optional

# Stance type for evidence items
Stance = Literal["supports", "refutes", "neutral"]


@dataclass
class EvidenceItem:
    """A single evidence item from RAG or SERP (internal)."""

    title: str
    url: str
    snippet: str
    source: str = ""  # e.g. "serp" or "rag" or domain
    score: float = 0.0
    stance: Optional[Stance] = None


@dataclass
class Citation:
    """Citation for API response (title, url, snippet only)."""

    title: str
    url: str
    snippet: str
