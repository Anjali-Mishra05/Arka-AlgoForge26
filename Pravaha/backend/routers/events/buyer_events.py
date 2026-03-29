"""
buyer_events.py — Public API endpoints for buyer interaction events.

These are called by the frontend proposal viewer (no JWT required —
buyers are not authenticated). Each endpoint records the event,
updates the engagement score, and emits to the event bus.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from utils.engagement import record_buyer_event, calculate_engagement_score
from utils.event_bus import emit

router = APIRouter(prefix="/events/buyer", tags=["buyer-events"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PageViewRequest(BaseModel):
    proposal_id: str
    buyer_email: Optional[str] = ""
    buyer_name: Optional[str] = ""
    is_repeat: bool = False


class QuestionRequest(BaseModel):
    proposal_id: str
    buyer_email: Optional[str] = ""
    question: str = ""


class CtaClickRequest(BaseModel):
    proposal_id: str
    buyer_email: Optional[str] = ""
    cta_label: Optional[str] = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/page-view")
async def record_page_view(body: PageViewRequest) -> Dict[str, Any]:
    """Called when a buyer opens a proposal link."""
    event_type = "repeat_visit" if body.is_repeat else "proposal_opened"

    score_doc = record_buyer_event(
        proposal_id=body.proposal_id,
        event_type=event_type,
        buyer_email=body.buyer_email or "",
        extra={"buyer_name": body.buyer_name},
    )

    try:
        emit("buyer.proposal_opened", {
            "proposal_id": body.proposal_id,
            "buyer_email": body.buyer_email,
            "buyer_name": body.buyer_name,
            "is_repeat": body.is_repeat,
            "engagement_score": score_doc.get("score", 0),
            "tier": score_doc.get("tier", "cold"),
        })
    except Exception:
        pass  # Non-blocking

    return {"status": "recorded", "score": score_doc.get("score", 0), "tier": score_doc.get("tier", "cold")}


@router.post("/question")
async def record_question(body: QuestionRequest) -> Dict[str, Any]:
    """Called when a buyer submits a question in proposal chat."""
    score_doc = record_buyer_event(
        proposal_id=body.proposal_id,
        event_type="question_asked",
        buyer_email=body.buyer_email or "",
        extra={"question_preview": body.question[:120]},
    )

    try:
        emit("buyer.question_asked", {
            "proposal_id": body.proposal_id,
            "buyer_email": body.buyer_email,
            "question": body.question,
            "engagement_score": score_doc.get("score", 0),
            "tier": score_doc.get("tier", "cold"),
        })
    except Exception:
        pass

    return {"status": "recorded", "score": score_doc.get("score", 0), "tier": score_doc.get("tier", "cold")}


@router.post("/cta-click")
async def record_cta_click(body: CtaClickRequest) -> Dict[str, Any]:
    """Called when a buyer clicks a CTA in a proposal."""
    score_doc = record_buyer_event(
        proposal_id=body.proposal_id,
        event_type="cta_clicked",
        buyer_email=body.buyer_email or "",
        extra={"cta_label": body.cta_label},
    )

    try:
        emit("buyer.cta_clicked", {
            "proposal_id": body.proposal_id,
            "buyer_email": body.buyer_email,
            "cta_label": body.cta_label,
            "engagement_score": score_doc.get("score", 0),
            "tier": score_doc.get("tier", "cold"),
        })
    except Exception:
        pass

    return {"status": "recorded", "score": score_doc.get("score", 0), "tier": score_doc.get("tier", "cold")}


@router.get("/score/{proposal_id}")
async def get_score(proposal_id: str) -> Dict[str, Any]:
    """Return the current engagement score for a proposal."""
    return calculate_engagement_score(proposal_id)
