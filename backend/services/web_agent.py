"""
WEB Agent: use Search Planner and SERP client to gather live web evidence.
Returns list of EvidenceItem; deduplicates by URL.
"""

import logging
from typing import List

from backend.models import EvidenceItem
from backend.services.search_planner import plan_queries
from backend.services.serp_client import search

logger = logging.getLogger(__name__)


def fetch_evidence(claim: str, num_per_query: int = 5) -> List[EvidenceItem]:
    """
    Plan queries from claim, run SERP for each, merge and dedupe by URL.
    Returns list of EvidenceItem with source="serp". On SERP failure returns [].
    """
    queries = plan_queries(claim)
    if not queries:
        return []
    seen_urls: set[str] = set()
    items: List[EvidenceItem] = []
    for q in queries:
        try:
            raw = search(query=q, num_results=num_per_query)
            for r in raw:
                url = (r.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                items.append(
                    EvidenceItem(
                        title=r.get("title") or "",
                        url=url,
                        snippet=r.get("snippet") or "",
                        source="serp",
                        score=0.0,
                    )
                )
        except Exception as e:
            logger.warning("WEB agent SERP call failed for query %s: %s", q[:50], e)
            continue
    return items
