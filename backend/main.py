"""
FastAPI application for the News Claim Verification backend.
Exposes /health and /verify for the browser extension.
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.claim_intake import normalize, validate
from backend.services.orchestrator import run_verification
from backend.services.review_store import add_pending, get_pending_ids, get_pending_item, submit_review

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="News Claim Verification API",
    description="RAG/agentic pipeline for verifying claims with citations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check for load balancers and extension."""
    return {"status": "ok"}


class VerifyRequest(BaseModel):
    """Request body for POST /verify."""

    claim: str = ""


class ReviewRequest(BaseModel):
    """Request body for POST /review/{claim_id}."""

    verdict: Optional[str] = None
    reasoning: Optional[str] = None


@app.post("/verify")
def verify(request: VerifyRequest):
    """
    Verify a claim. Accepts { "claim": str }, returns verdict, reasoning, citations.
    """
    raw_claim = request.claim or ""
    ok, err = validate(raw_claim)
    if not ok:
        raise HTTPException(status_code=400, detail=err or "Invalid claim.")
    claim = normalize(raw_claim)
    claim_hash = hashlib.sha256(claim.encode()).hexdigest()[:16]
    claim_id = f"{claim_hash}_{int(time.time())}"
    start = time.perf_counter()
    try:
        result = run_verification(claim, claim_id=claim_id)
        elapsed = time.perf_counter() - start
        if result.get("requires_review") and result.get("claim_id"):
            add_pending(
                result["claim_id"],
                claim,
                result["verdict"],
                result["reasoning"],
                result["citations"],
            )
        # Do not expose HITL fields to extension
        out = {k: v for k, v in result.items() if k not in ("requires_review", "claim_id")}
        logger.info(
            "verify claim_hash=%s verdict=%s citations=%s elapsed_sec=%.2f",
            claim_hash,
            out.get("verdict"),
            len(out.get("citations", [])),
            elapsed,
        )
        return out
    except Exception as e:
        logger.exception("verify failed claim_hash=%s: %s", claim_hash, e)
        raise HTTPException(
            status_code=503,
            detail="Verification temporarily unavailable. Please try again.",
        )


@app.get("/pending_reviews")
def pending_reviews():
    """Return list of claim_ids awaiting human review (HITL)."""
    return {"claim_ids": get_pending_ids()}


@app.get("/pending_reviews/{claim_id}")
def get_review(claim_id: str):
    """Get stored draft for a claim_id (for reviewer UI)."""
    item = get_pending_item(claim_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found.")
    return item


@app.post("/review/{claim_id}")
def review_claim(claim_id: str, body: ReviewRequest):
    """Human approve or override verdict/reasoning; remove from pending."""
    verdict = body.verdict
    reasoning = body.reasoning
    ok = submit_review(claim_id, verdict=verdict, reasoning=reasoning)
    if not ok:
        raise HTTPException(status_code=404, detail="Not found.")
    return {"status": "ok"}
