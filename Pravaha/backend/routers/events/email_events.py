"""
email_events.py — Email campaign event endpoint.

Emits email.campaign_sent after a bulk email campaign is dispatched.
Called alongside (not replacing) the existing sendbulk endpoint.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from utils.event_bus import emit

router = APIRouter(prefix="/events/email", tags=["email-events"])


class CampaignSentRequest(BaseModel):
    campaign_id: Optional[str] = ""
    subject: str
    recipient_count: int
    successful_sends: int
    failed_sends: int = 0
    sent_by: Optional[str] = ""


@router.post("/campaign-sent")
async def campaign_sent(body: CampaignSentRequest) -> Dict[str, Any]:
    """Emit email.campaign_sent event after a bulk campaign is dispatched."""
    try:
        emit("email.campaign_sent", {
            "campaign_id": body.campaign_id,
            "subject": body.subject,
            "recipient_count": body.recipient_count,
            "successful_sends": body.successful_sends,
            "failed_sends": body.failed_sends,
            "sent_by": body.sent_by,
        })
    except Exception:
        pass

    return {"status": "emitted", "event": "email.campaign_sent"}
