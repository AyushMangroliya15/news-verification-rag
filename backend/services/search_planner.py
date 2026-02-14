"""
Search Planner: generate multiple search queries from a claim for SERP.
Rule-based for predictability; can be extended with LLM later.
"""

from typing import List


def plan_queries(claim: str) -> List[str]:
    """
    Generate 2–4 search queries for the claim: as-is, fact-check variant, optional debunk.
    """
    claim = (claim or "").strip()
    if not claim:
        return []
    queries: List[str] = []
    # 1) Claim as-is
    queries.append(claim)
    # 2) Fact check framing
    queries.append(f"fact check {claim}")
    # 3) Shorter: first ~80 chars if long (better for some SERP)
    if len(claim) > 80:
        short = claim[:77].rsplit(" ", 1)[0] if " " in claim[:77] else claim[:77]
        if short and short not in queries:
            queries.append(short)
    # 4) Debunk framing (for refuting evidence)
    debunk = f'"{claim}" debunk'
    if debunk not in queries:
        queries.append(debunk)
    return queries[:4]
