"""
Tavily API client: run web search optimized for AI/LLM applications.
Returns article-specific URLs with high relevance scores.
Designed for fact-checking and citation use cases.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests

from backend.config import TAVILY_API_KEY, TAVILY_NUM_RESULTS, TAVILY_REQUEST_TIMEOUT_SEC

logger = logging.getLogger(__name__)


def search(
    query: str,
    num_results: int | None = None,
    domain_hint: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Run a search via Tavily API. Returns list of dicts with title, url, snippet.
    Tavily is designed for AI applications and returns article-specific URLs by default.
    """
    logger.info("Tavily API: Searching for '%s' (max_results=%d)", query[:100], num_results or TAVILY_NUM_RESULTS)
    
    if not TAVILY_API_KEY or not query.strip():
        if not TAVILY_API_KEY:
            logger.warning("Tavily API key not configured")
        return []
    
    num = num_results if num_results is not None else TAVILY_NUM_RESULTS
    q = query.strip()
    
    # Build request payload
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": q,
        "search_depth": "basic",  # Options: "basic" or "advanced"
        "include_answer": False,  # We just want search results
        "include_raw_content": False,
        "max_results": min(num, 20),  # Tavily allows up to 20 results per request
    }
    
    # Add domain filter if specified
    if domain_hint and domain_hint.strip():
        payload["include_domains"] = [domain_hint.strip()]
        logger.info("Tavily API: Using domain filter: %s", domain_hint.strip())
    
    url = "https://api.tavily.com/search"
    logger.debug("Tavily API request payload: %s", {k: v for k, v in payload.items() if k != "api_key"})
    
    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=TAVILY_REQUEST_TIMEOUT_SEC,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        logger.debug("Tavily API response status: %d", resp.status_code)
    except requests.RequestException as e:
        logger.warning("Tavily API request failed: %s", e)
        return []
    except ValueError as e:
        logger.warning("Tavily API JSON decode failed: %s", e)
        return []

    error = data.get("error")
    if error:
        logger.warning("Tavily API error: %s", error)
        return []

    raw_results = data.get("results") or []
    logger.info("Tavily API response: received %d raw results", len(raw_results))
    
    results: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_results, 1):
        url_str = (item.get("url") or "").strip()
        if not url_str:
            logger.debug("Tavily result #%d: Skipping item with no URL", idx)
            continue
        
        title = (item.get("title") or "").strip() or "No title"
        # Tavily provides 'content' field which is the article snippet
        snippet = (item.get("content") or item.get("snippet") or "").strip()
        
        # Log each result being processed
        logger.info(
            "Tavily result #%d: URL=%s | Title=%s | Snippet=%s",
            idx,
            url_str,
            title[:60] + "..." if len(title) > 60 else title,
            snippet[:80] + "..." if len(snippet) > 80 else snippet[:80] if snippet else "(no snippet)",
        )
        
        results.append(
            {
                "title": title[:500],
                "url": url_str,
                "snippet": snippet[:1000],
            }
        )
    
    logger.info(
        "Tavily search completed: query='%s' | returned %d valid results out of %d raw results",
        q[:50],
        len(results),
        len(raw_results),
    )
    
    # Log summary of URLs returned
    if results:
        logger.info("Tavily result URLs:")
        for idx, result in enumerate(results, 1):
            logger.info("  %d. %s", idx, result["url"])
    
    return results

