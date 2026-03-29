"""
call_events.py — Post-call event endpoints.

Called after a call summary is saved. Emits specific events based on
what was detected in the call (objections, intent signals, etc.).
Does NOT modify the existing VAPI webhook handler.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from utils.database import APP_DB_NAME, Database
from utils.event_bus import emit

router = APIRouter(prefix="/events/call", tags=["call-events"])

# Keywords used to classify call signals (mirrors existing intelligence logic)
_OBJECTION_KEYWORDS = [
    "budget", "cost", "price", "expensive", "afford",
    "timeline", "deadline", "too long", "approval", "decision",
    "competitor", "alternative", "other vendor",
]
_HIGH_INTENT_KEYWORDS = [
    "ready to move forward", "next steps", "sign", "contract",
    "purchase", "buy", "implement", "go ahead", "looks good",
    "interested", "let's do it",
]


class CallCompletedRequest(BaseModel):
    call_id: str
    summary: Optional[str] = None
    phone: Optional[str] = ""
    contact_name: Optional[str] = ""
    duration_seconds: Optional[int] = None


@router.post("/completed")
async def call_completed(body: CallCompletedRequest) -> Dict[str, Any]:
    """Emit post-call events after a call summary is processed.

    Can be called directly after /admin/call finishes, or triggered
    from a VAPI webhook callback.
    """
    app_db = Database(APP_DB_NAME)

    # Fetch summary from DB if not provided inline
    summary = body.summary or ""
    if not summary and body.call_id:
        call_doc = app_db.calls_col.find_one({"call_id": body.call_id}, {"summary": 1})
        if call_doc:
            summary = call_doc.get("summary", "")

    summary_lower = summary.lower()

    # Always emit call.completed
    base_payload = {
        "call_id": body.call_id,
        "phone": body.phone,
        "contact_name": body.contact_name,
        "duration_seconds": body.duration_seconds,
        "summary_preview": summary[:300] if summary else "",
    }

    try:
        emit("call.completed", base_payload)
    except Exception:
        pass

    emitted: list[str] = ["call.completed"]

    # Detect objections
    detected_objections = [kw for kw in _OBJECTION_KEYWORDS if kw in summary_lower]
    if detected_objections:
        try:
            emit("call.objection_detected", {
                **base_payload,
                "objections": detected_objections,
            })
            emitted.append("call.objection_detected")
        except Exception:
            pass

    # Detect high intent
    detected_intent = [kw for kw in _HIGH_INTENT_KEYWORDS if kw in summary_lower]
    if detected_intent:
        try:
            emit("call.high_intent", {
                **base_payload,
                "intent_signals": detected_intent,
            })
            emitted.append("call.high_intent")
        except Exception:
            pass

    return {"status": "emitted", "events": emitted}
