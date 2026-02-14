"""
Source credibility: filter citations to allowed (credible) domains only.
Uses a configurable domain allowlist; malformed URLs are treated as not credible.
"""

from __future__ import annotations

from typing import List
from urllib.parse import urlparse

from backend.models import Citation


def _domain_from_url(url: str) -> str | None:
    """
    Extract the netloc (host) from a URL, lowercased and without leading 'www.'.
    Returns None for empty or malformed URLs.
    """
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url:
        return None
    try:
        parsed = urlparse(url)
        netloc = (parsed.netloc or "").strip().lower()
        if not netloc:
            return None
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc if netloc else None
    except Exception:
        return None


def is_credible_url(url: str, allowed_domains: set[str]) -> bool:
    """
    Return True if the URL's domain is in the allowed_domains set.
    Empty url or unknown/malformed URL returns False.
    """
    if not allowed_domains:
        return False
    domain = _domain_from_url(url)
    return domain is not None and domain in allowed_domains


def filter_credible_citations(
    citations: List[Citation],
    allowed_domains: set[str],
) -> List[Citation]:
    """
    Return only citations whose URL belongs to an allowed domain.
    Order is preserved. Empty allowed_domains returns empty list.
    """
    if not citations or not allowed_domains:
        return list(citations) if allowed_domains else []
    return [c for c in citations if is_credible_url(c.url, allowed_domains)]
