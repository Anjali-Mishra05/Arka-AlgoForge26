"""
Coaching router — history, analytics, playbook, leaderboard, tip feedback.
Mounted at /admin/coaching via routers/admin/__init__.py
"""
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from utils.auth import is_admin
from utils.database import db

router = APIRouter(prefix="/coaching", tags=["coaching"])


# ── Models ───────────────────────────────────────────────────────────────────

class TipFeedbackRequest(BaseModel):
    feedback: str = Field(pattern="^(helpful|not_relevant|used)$")

class PlaybookEntryRequest(BaseModel):
    entry_id: Optional[str] = None
    category: str = Field(pattern="^(objection|signal|question)$")
    trigger_phrase: str = Field(min_length=2, max_length=200)
    label: str = Field(min_length=2, max_length=100)
    suggested_response: str = Field(min_length=5, max_length=500)
    urgency: str = Field(default="medium", pattern="^(high|medium|low)$")
    priority: int = Field(default=5, ge=1, le=10)
    enabled: bool = True


# ── Coaching Stats ────────────────────────────────────────────────────────────

@router.get("/stats")
async def coaching_stats(days: int = 30, _: dict = Depends(is_admin)):
    """Aggregate coaching analytics for the last N days."""
    return db.get_coaching_stats(days=days)


# ── Coaching History ──────────────────────────────────────────────────────────

@router.get("/history")
async def coaching_history(
    limit: int = 50,
    rep_id: Optional[str] = None,
    _: dict = Depends(is_admin),
):
    """Recent coaching tips, optionally filtered by rep."""
    return db.get_coaching_history(limit=limit, rep_id=rep_id)


@router.get("/history/{call_id}")
async def coaching_history_for_call(call_id: str, _: dict = Depends(is_admin)):
    """All coaching tips for a specific call."""
    tips = db.get_coaching_tips_for_call(call_id)
    return {"call_id": call_id, "tips": tips, "total": len(tips)}


# ── Tip Feedback ──────────────────────────────────────────────────────────────

@router.post("/tip/{tip_id}/feedback")
async def submit_tip_feedback(
    tip_id: str,
    body: TipFeedbackRequest,
    current_user: dict = Depends(is_admin),
):
    """Rep marks a coaching tip as helpful / not_relevant / used."""
    rep_id = current_user.get("username") or current_user.get("email", "unknown")
    updated = db.update_coaching_tip_feedback(tip_id, body.feedback, rep_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Tip not found")
    return {"tip_id": tip_id, "feedback": body.feedback}


# ── Leaderboard ───────────────────────────────────────────────────────────────

@router.get("/leaderboard")
async def coaching_leaderboard(days: int = 30, _: dict = Depends(is_admin)):
    """Per-rep coaching stats sorted by helpful tip count."""
    return db.get_coaching_leaderboard(days=days)


# ── Playbook ──────────────────────────────────────────────────────────────────

@router.get("/playbook")
async def get_playbook(_: dict = Depends(is_admin)):
    """List all custom coaching playbook entries."""
    return db.get_coaching_playbook()


@router.post("/playbook")
async def upsert_playbook_entry(
    body: PlaybookEntryRequest,
    current_user: dict = Depends(is_admin),
):
    """Create or update a coaching playbook entry."""
    entry = body.model_dump()
    if not entry.get("entry_id"):
        entry["entry_id"] = str(uuid4())
    entry["created_by"] = current_user.get("username") or current_user.get("email", "unknown")
    db.upsert_playbook_entry(entry)
    return {"entry_id": entry["entry_id"], "status": "saved"}


@router.delete("/playbook/{entry_id}")
async def delete_playbook_entry(entry_id: str, _: dict = Depends(is_admin)):
    """Delete a coaching playbook entry."""
    deleted = db.delete_playbook_entry(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"entry_id": entry_id, "status": "deleted"}
