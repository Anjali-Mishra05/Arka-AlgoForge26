"""
engagement.py — Buyer engagement scoring engine.

Scores buyer activity per proposal and emits events when thresholds
are crossed. Does NOT touch any existing proposal or chat code.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from utils.database import APP_DB_NAME, Database
from utils.event_bus import emit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights (points per action)
# ---------------------------------------------------------------------------

SCORE_WEIGHTS: Dict[str, int] = {
    "proposal_opened":      10,
    "repeat_visit":         15,
    "question_asked":       25,
    "cta_clicked":          30,
    "time_on_page_minute":   5,   # Future: when frontend sends dwell time
}

# Tier thresholds (score → tier)
TIER_THRESHOLDS = [
    (60, "hot"),
    (25, "warm"),
    (0,  "cold"),
]


def _score_to_tier(score: int) -> str:
    for threshold, tier in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "cold"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def record_buyer_event(
    proposal_id: str,
    event_type: str,
    buyer_email: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record a buyer interaction and recalculate the engagement score.

    *event_type* must be one of the keys in SCORE_WEIGHTS.
    Returns the updated score document.
    """
    if event_type not in SCORE_WEIGHTS:
        logger.warning("engagement: unknown event type '%s'", event_type)

    points = SCORE_WEIGHTS.get(event_type, 0)
    app_db = Database(APP_DB_NAME)

    event_doc = {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "points": points,
        "buyer_email": buyer_email,
        **(extra or {}),
    }

    # Append to event log
    app_db.append_engagement_event(proposal_id, event_doc)

    # Recalculate total score and emit if threshold crossed
    return _recalculate_and_emit(proposal_id, buyer_email, app_db)


def calculate_engagement_score(proposal_id: str) -> Dict[str, Any]:
    """Return the current score document for a proposal (read-only)."""
    app_db = Database(APP_DB_NAME)
    doc = app_db.get_engagement_score(proposal_id)
    if not doc:
        return {
            "proposal_id": proposal_id,
            "score": 0,
            "tier": "cold",
            "events": [],
        }
    return doc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _recalculate_and_emit(
    proposal_id: str,
    buyer_email: str,
    app_db: Database,
) -> Dict[str, Any]:
    doc = app_db.get_engagement_score(proposal_id) or {}
    events = doc.get("events", [])

    total = sum(e.get("points", 0) for e in events)
    previous_tier = doc.get("tier", "cold")
    new_tier = _score_to_tier(total)

    updated = {
        "proposal_id": proposal_id,
        "buyer_email": buyer_email or doc.get("buyer_email", ""),
        "score": total,
        "tier": new_tier,
    }
    app_db.upsert_engagement_score(proposal_id, updated)

    # Emit tier-change event when buyer crosses into "hot"
    if new_tier == "hot" and previous_tier != "hot":
        try:
            emit("buyer.high_engagement", {
                "proposal_id": proposal_id,
                "buyer_email": updated["buyer_email"],
                "score": total,
                "tier": new_tier,
                "previous_tier": previous_tier,
            })
        except Exception:
            logger.exception("engagement: failed to emit buyer.high_engagement")

    updated["events"] = events
    return updated
