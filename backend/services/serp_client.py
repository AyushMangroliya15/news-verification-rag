"""
SERP API client: run web search and return normalized results (title, url, snippet).
On failure returns empty list; errors are logged.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import urlencode

import requests

from backend.config import (
    SERP_API_BASE_URL,
    SERP_API_KEY,
    SERP_NUM_RESULTS,
    SERP_REQUEST_TIMEOUT_SEC,
)

logger = logging.getLogger(__name__)


def search(
    query: str,
    num_results: int | None = None,
    domain_hint: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Run a Google search via SerpAPI. Returns list of dicts with title, url, snippet.
    domain_hint can be used to build a site: query if the API supports it;
    otherwise we append to q. On timeout or API error returns [].
    """
    if not SERP_API_KEY or not query.strip():
        return []
    num = num_results if num_results is not None else SERP_NUM_RESULTS
    q = query.strip()
    if domain_hint and domain_hint.strip():
        q = f"site:{domain_hint.strip()} {q}"
    params = {
        "engine": "google",
        "q": q,
        "api_key": SERP_API_KEY,
        "num": min(num, 20),
    }
    url = f"{SERP_API_BASE_URL.rstrip('/')}?{urlencode(params)}"
    try:
        resp = requests.get(url, timeout=SERP_REQUEST_TIMEOUT_SEC)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("SERP request failed: %s", e)
        return []
    except ValueError as e:
        logger.warning("SERP JSON decode failed: %s", e)
        return []

    error = data.get("error")
    if error:
        logger.warning("SERP API error: %s", error)
        return []

    results: List[Dict[str, Any]] = []
    for item in data.get("organic_results") or []:
        link = (item.get("link") or "").strip()
        if not link:
            continue
        title = (item.get("title") or "").strip() or "No title"
        snippet = (item.get("snippet") or item.get("description") or "").strip()
        results.append(
            {
                "title": title[:500],
                "url": link,
                "snippet": snippet[:1000],
            }
        )
    return results
