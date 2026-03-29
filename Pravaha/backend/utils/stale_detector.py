"""
stale_detector.py — Background job that detects stale proposals.

Runs on a schedule (via APScheduler, already used in the project).
Finds proposals not viewed in STALE_AFTER_HOURS and emits
proposal.stale for each. Does NOT modify any existing automation code.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from utils.database import APP_DB_NAME, Database
from utils.event_bus import emit

logger = logging.getLogger(__name__)

STALE_AFTER_HOURS = 48


def detect_stale_proposals() -> List[Dict[str, Any]]:
    """Find proposals not viewed in the last STALE_AFTER_HOURS hours.

    Emits proposal.stale for each stale proposal found.
    Returns list of stale proposal dicts.
    """
    app_db = Database(APP_DB_NAME)
    cutoff = datetime.utcnow() - timedelta(hours=STALE_AFTER_HOURS)

    # Query proposals: either never viewed (no last_viewed_at) or viewed
    # before cutoff. We look at the proposals collection only.
    stale_docs = list(app_db.proposals_col.find(
        {
            "$or": [
                {"last_viewed_at": {"$lt": cutoff}},
                {"last_viewed_at": {"$exists": False}},
            ],
            "created_at": {"$lt": cutoff},  # Skip brand-new proposals
        },
        {
            "_id": 0,
            "proposal_id": 1,
            "title": 1,
            "created_by": 1,
            "created_at": 1,
            "last_viewed_at": 1,
        },
    ).limit(50))  # Process max 50 per run to avoid overload

    emitted_ids: List[str] = []
    for doc in stale_docs:
        proposal_id = doc.get("proposal_id", "")
        if not proposal_id:
            continue
        try:
            emit("proposal.stale", {
                "proposal_id": proposal_id,
                "title": doc.get("title", ""),
                "created_by": doc.get("created_by", ""),
                "created_at": (
                    doc["created_at"].isoformat()
                    if isinstance(doc.get("created_at"), datetime)
                    else str(doc.get("created_at", ""))
                ),
                "last_viewed_at": (
                    doc["last_viewed_at"].isoformat()
                    if isinstance(doc.get("last_viewed_at"), datetime)
                    else None
                ),
                "stale_after_hours": STALE_AFTER_HOURS,
            })
            emitted_ids.append(proposal_id)
        except Exception:
            logger.exception("stale_detector: failed to emit for proposal %s", proposal_id)

    if emitted_ids:
        logger.info("stale_detector: emitted proposal.stale for %d proposals", len(emitted_ids))

    return stale_docs
