"""
zapier_webhooks.py — Outbound Zapier webhook engine.

Fires payloads to user-configured Zapier catch-hook URLs when Pravaha
events occur. Logs every attempt to sync_log. Completely non-blocking
for the caller — errors are caught and logged.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from utils.database import APP_DB_NAME, Database
from utils.event_bus import EVENTS, on

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10


# ---------------------------------------------------------------------------
# Core fire function
# ---------------------------------------------------------------------------

def fire_webhooks(
    event_type: str,
    payload: Dict[str, Any],
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fire all enabled webhooks registered for *event_type*.

    Returns a list of per-webhook result dicts with keys:
        webhook_id, label, status ("success"|"failed"), error
    """
    app_db = Database(APP_DB_NAME)
    webhooks = app_db.get_webhooks_for_event(event_type)
    results: List[Dict[str, Any]] = []

    if not webhooks:
        return results

    body = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "pravaha",
        "data": payload,
    }

    for wh in webhooks:
        webhook_id = wh["webhook_id"]
        url = wh["webhook_url"]
        label = wh.get("label", "")
        status = "failed"
        error_msg: Optional[str] = None

        try:
            resp = requests.post(
                url,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT_SECONDS,
            )
            if resp.status_code < 400:
                status = "success"
            else:
                error_msg = f"HTTP {resp.status_code}"
        except requests.Timeout:
            error_msg = "Request timed out"
        except requests.RequestException as exc:
            error_msg = str(exc)

        # Persist fire record
        try:
            app_db.record_webhook_fire(webhook_id, status)
            app_db.log_sync_event(
                event=event_type,
                provider="zapier",
                entity_id=webhook_id,
                status=status,
                data={"label": label, "url": url[:60]},
                error=error_msg,
            )
        except Exception:
            logger.exception("zapier_webhooks: failed to record fire for webhook %s", webhook_id)

        result = {"webhook_id": webhook_id, "label": label, "status": status}
        if error_msg:
            result["error"] = error_msg
        results.append(result)

        if status == "failed":
            logger.warning(
                "zapier_webhooks: webhook '%s' (%s) failed for event '%s': %s",
                label, webhook_id, event_type, error_msg,
            )
        else:
            logger.info(
                "zapier_webhooks: fired '%s' → %s", event_type, label
            )

    return results


def test_webhook(webhook_id: str) -> Dict[str, Any]:
    """Send a test payload to a single webhook by ID."""
    app_db = Database(APP_DB_NAME)
    wh = app_db.get_zapier_webhook(webhook_id)
    if not wh:
        return {"error": "Webhook not found"}

    test_payload = {
        "event": wh["event_type"],
        "timestamp": datetime.utcnow().isoformat(),
        "source": "pravaha",
        "data": {"test": True, "message": "This is a test payload from Pravaha"},
    }

    try:
        resp = requests.post(
            wh["webhook_url"],
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
        status = "success" if resp.status_code < 400 else "failed"
        return {"status": status, "http_status": resp.status_code}
    except requests.Timeout:
        return {"status": "failed", "error": "Request timed out"}
    except requests.RequestException as exc:
        return {"status": "failed", "error": str(exc)}


# ---------------------------------------------------------------------------
# Wire up: listen to every event and fire matching webhooks
# ---------------------------------------------------------------------------

def _zapier_listener(event_type: str, payload: Dict[str, Any]) -> None:
    fire_webhooks(event_type, payload)


def register_zapier_listeners() -> None:
    """Call once at startup to connect event_bus → Zapier webhook engine."""
    for event_type in EVENTS:
        on(event_type, _zapier_listener)
    logger.info("zapier_webhooks: registered listeners for %d event types", len(EVENTS))
