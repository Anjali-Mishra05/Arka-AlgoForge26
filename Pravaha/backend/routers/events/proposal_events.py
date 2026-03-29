"""
proposal_events.py — Proposal lifecycle event endpoint.

Emits proposal.generated after a proposal is created.
Called alongside (not replacing) the existing generation endpoint.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from utils.event_bus import emit

router = APIRouter(prefix="/events/proposal", tags=["proposal-events"])


class ProposalGeneratedRequest(BaseModel):
    proposal_id: str
    created_by: str
    title: Optional[str] = ""
    documents_used: Optional[List[str]] = []
    proposal_url: Optional[str] = ""


@router.post("/generated")
async def proposal_generated(body: ProposalGeneratedRequest) -> Dict[str, Any]:
    """Emit proposal.generated event after a proposal is created."""
    try:
        emit("proposal.generated", {
            "proposal_id": body.proposal_id,
            "created_by": body.created_by,
            "title": body.title,
            "documents_used": body.documents_used,
            "proposal_url": body.proposal_url,
        })
    except Exception:
        pass

    return {"status": "emitted", "event": "proposal.generated"}
