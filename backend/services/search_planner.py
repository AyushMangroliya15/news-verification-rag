"""
Search Planner: generate multiple search queries from a claim for Tavily search.
Rule-based for predictability; can be extended with LLM later.
"""

import re
from typing import List


def _extract_key_phrases(claim: str) -> List[str]:
    """
    Extract key phrases from claim that should be quoted for better search results.
    Returns list of phrases (typically 2-5 words) that are likely important.
    """
    # Remove common fact-checking prefixes
    claim_clean = re.sub(r'^(fact check|is it true that|did|does|was|were)\s+', '', claim.lower())
    
    # Find quoted phrases first (these are definitely important)
    quoted = re.findall(r'"([^"]+)"', claim)
    if quoted:
        return quoted
    
    # Find capitalized phrases (proper nouns, titles)
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', claim)
    if capitalized:
        # Take the longest capitalized phrase as most important
        return [max(capitalized, key=len)]
    
    # Extract noun phrases (simple heuristic: sequences of 2-4 words)
    words = claim.split()
    phrases = []
    for i in range(len(words) - 1):
        # 2-word phrases
        if i + 1 < len(words):
            phrases.append(f"{words[i]} {words[i+1]}")
        # 3-word phrases
        if i + 2 < len(words):
            phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
    
    # Return the longest phrase found, or empty if none
    if phrases:
        return [max(phrases, key=len)]
    return []


def plan_queries(claim: str) -> List[str]:
    """
    Generate 2–4 search queries for the claim with improved specificity.
    Uses quoted key phrases to get better article-specific results.
    """
    claim = (claim or "").strip()
    if not claim:
        return []
    queries: List[str] = []
    
    # Extract key phrases for quoting
    key_phrases = _extract_key_phrases(claim)
    
    # 1) Claim with quoted key phrases (most specific)
    if key_phrases:
        # Replace key phrase in claim with quoted version (case-insensitive)
        phrase = key_phrases[0]  # Use first/longest phrase
        # Find the phrase in the original claim (preserving case)
        pattern = re.escape(phrase)
        if re.search(pattern, claim, re.IGNORECASE):
            # Replace with quoted version, preserving original case
            query1 = re.sub(pattern, f'"{phrase}"', claim, flags=re.IGNORECASE)
        else:
            # If not found, just add quotes around the phrase
            query1 = claim.replace(phrase, f'"{phrase}"')
        queries.append(query1)
    else:
        # Fallback: claim as-is
        queries.append(claim)
    
    # 2) Fact check framing with quoted phrase
    if key_phrases:
        fact_check_query = f'fact check "{key_phrases[0]}"'
        queries.append(fact_check_query)
    else:
        queries.append(f"fact check {claim}")
    
    # 3) Direct quote search (if we have a key phrase)
    if key_phrases:
        quoted_query = f'"{key_phrases[0]}"'
        if len(key_phrases[0]) > 10:  # Only if phrase is substantial
            queries.append(quoted_query)
    
    # 4) Shorter version if claim is long (better for search APIs)
    if len(claim) > 80:
        short = claim[:77].rsplit(" ", 1)[0] if " " in claim[:77] else claim[:77]
        if short and short not in queries:
            queries.append(short)
    
    # 5) Debunk framing (for refuting evidence) - only if we have space
    if len(queries) < 4:
        if key_phrases:
            debunk = f'"{key_phrases[0]}" debunk'
        else:
            debunk = f'"{claim}" debunk'
        if debunk not in queries:
            queries.append(debunk)
    
    return queries[:4]
