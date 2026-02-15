"""
FastAPI application for the News Claim Verification backend.
Exposes /health and /verify for the browser extension.
"""
from __future__ import annotations

import hashlib
import logging
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.claim_intake import normalize, validate
from backend.services.orchestrator import run_verification

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


@app.get("/status")
def status():
    """Return system status including configured search provider."""
    from backend.config import TAVILY_API_KEY
    
    has_tavily = bool(TAVILY_API_KEY)
    
    return {
        "status": "ok",
        "search_provider": "tavily",
        "tavily_api_key": "configured" if has_tavily else "not configured",
    }


class VerifyRequest(BaseModel):
    """Request body for POST /verify."""

    claim: str = ""


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
    start = time.perf_counter()
    try:
        result = run_verification(claim)
        elapsed = time.perf_counter() - start
        logger.info(
            "verify claim_hash=%s verdict=%s citations=%s elapsed_sec=%.2f",
            claim_hash,
            result.get("verdict"),
            len(result.get("citations", [])),
            elapsed,
        )
        return result
    except Exception as e:
        logger.exception("verify failed claim_hash=%s: %s", claim_hash, e)
        raise HTTPException(
            status_code=503,
            detail="Verification temporarily unavailable. Please try again.",
        )

