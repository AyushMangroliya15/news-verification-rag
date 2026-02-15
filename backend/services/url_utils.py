"""
URL utilities: homepage detection and URL validation.
Utility functions for filtering homepage URLs from search results.
"""
from __future__ import annotations

from urllib.parse import urlparse


def _is_homepage_url(url: str) -> bool:
    """
    Detect if a URL is likely a homepage rather than a specific article.
    Returns True if the URL appears to be a homepage.
    """
    if not url or not isinstance(url, str):
        return True
    
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").strip()
        netloc = (parsed.netloc or "").lower()
        
        # Homepage indicators:
        # 1. Empty path or just "/"
        if not path or path == "/":
            return True
        
        # 2. Very short path (e.g., "/news", "/home", "/index")
        # Count path segments (excluding empty first segment)
        path_segments = [s for s in path.split("/") if s]
        
        # If only one segment, check if it's a homepage pattern
        if len(path_segments) == 1:
            single_segment = path_segments[0].lower()
            homepage_patterns = {
                "home", "index", "main", "default", "welcome",
                "news", "about", "contact", "search", "sitemap",
                "fact-check", "factcheck", "technology", "tech", "politics",
                "sports", "entertainment", "business", "world", "national",
                "local", "opinion", "lifestyle", "health", "science",
                "athletic", "sport", "sports", "athletics"
            }
            if single_segment in homepage_patterns:
                return True
        
        # 3. URL that's just the domain (with or without trailing slash)
        url_no_scheme = url.split("://", 1)[-1] if "://" in url else url
        url_no_scheme = url_no_scheme.split("?")[0].split("#")[0].rstrip("/")
        if url_no_scheme.lower() == netloc or url_no_scheme.lower() == f"www.{netloc}":
            return True
        
        # 4. Two-segment paths ending with "/" - check if second segment looks like an ID/article
        if len(path_segments) == 2 and path.endswith("/"):
            second_segment = path_segments[1]
            # If second segment looks like an ID (alphanumeric, UUID-like, or numeric), it's likely an article
            # IDs typically have: numbers, letters, hyphens, underscores, and are not generic words
            if (second_segment.replace("-", "").replace("_", "").isalnum() and 
                len(second_segment) > 5 and  # IDs are usually longer
                not second_segment.lower() in {"news", "articles", "stories", "posts"}):
                # This looks like an article ID, don't filter
                pass
            else:
                # Generic two-segment category page
                return True
        
        # 5. Single-segment paths ending with "/" that are generic categories
        if len(path_segments) == 1 and path.endswith("/"):
            # Check against all homepage patterns (not just a subset)
            if path_segments[0].lower() in homepage_patterns:
                return True
            
    except Exception:
        # If parsing fails, be conservative and treat as potentially valid
        return False
    
    return False

