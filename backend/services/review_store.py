"""
In-memory store for HITL: pending reviews keyed by claim_id.
Optional; for production use Redis or DB.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

_store: Dict[str, Dict[str, Any]] = {}


def add_pending(
    claim_id: str,
    claim: str,
    verdict: str,
    reasoning: str,
    citations: List[Dict[str, Any]],
) -> None:
    """Store a verification result that requires human review."""
    _store[claim_id] = {
        "claim": claim,
        "verdict": verdict,
        "reasoning": reasoning,
        "citations": citations,
        "created_at": time.time(),
    }


def get_pending_ids() -> List[str]:
    """Return list of claim_ids awaiting review."""
    return list(_store.keys())


def get_pending_item(claim_id: str) -> Dict[str, Any] | None:
    """Return stored item for claim_id or None."""
    return _store.get(claim_id)


def submit_review(
    claim_id: str,
    verdict: str | None = None,
    reasoning: str | None = None,
) -> bool:
    """
    Human approves or overrides; remove from pending. Returns True if claim_id was found.
    """
    if claim_id not in _store:
        return False
    item = _store.pop(claim_id)
    if verdict is not None:
        item["verdict"] = verdict
    if reasoning is not None:
        item["reasoning"] = reasoning
    return True
