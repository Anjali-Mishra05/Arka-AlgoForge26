"""
event_bus.py — Lightweight in-process pub/sub event bus.

New code emits events here; listeners (e.g. Zapier webhook engine,
MCP orchestrator) register handlers without touching existing modules.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported event types
# ---------------------------------------------------------------------------

EVENTS = {
    "buyer.proposal_opened",
    "buyer.question_asked",
    "buyer.cta_clicked",
    "buyer.high_engagement",
    "call.completed",
    "call.objection_detected",
    "call.high_intent",
    "email.campaign_sent",
    "proposal.generated",
    "proposal.stale",
    "automation.completed",
}

EVENT_DESCRIPTIONS: Dict[str, str] = {
    "buyer.proposal_opened":   "A buyer opened a shared proposal link",
    "buyer.question_asked":    "A buyer asked a question in proposal chat",
    "buyer.cta_clicked":       "A buyer clicked a CTA button in a proposal",
    "buyer.high_engagement":   "A buyer's engagement score crossed the 'hot' threshold",
    "call.completed":          "A sales call ended and the transcript was processed",
    "call.objection_detected": "An objection signal was detected in a call transcript",
    "call.high_intent":        "A high buying-intent signal was detected in a call",
    "email.campaign_sent":     "A bulk email campaign was sent",
    "proposal.generated":      "A new proposal was generated",
    "proposal.stale":          "A proposal has not been viewed for 48+ hours",
    "automation.completed":    "An internal automation finished executing",
}

# ---------------------------------------------------------------------------
# Internal registry
# ---------------------------------------------------------------------------

_listeners: Dict[str, List[Callable[[str, Dict[str, Any]], None]]] = {}


def on(event_type: str, handler: Callable[[str, Dict[str, Any]], None]) -> None:
    """Register a listener for an event type.

    The handler receives (event_type: str, payload: dict).
    Wildcard "*" receives every event.
    """
    if event_type not in EVENTS and event_type != "*":
        raise ValueError(f"Unknown event type: '{event_type}'. "
                         f"Known types: {sorted(EVENTS)}")
    _listeners.setdefault(event_type, []).append(handler)


def emit(event_type: str, payload: Dict[str, Any]) -> None:
    """Emit an event to all registered listeners.

    Errors in individual handlers are caught and logged so one bad
    handler never blocks the rest or the calling code.
    """
    if event_type not in EVENTS:
        logger.warning("event_bus.emit: unknown event type '%s' — emitting anyway", event_type)

    enriched = {
        **payload,
        "_event": event_type,
        "_emitted_at": datetime.utcnow().isoformat(),
    }

    targets: List[Callable] = (
        _listeners.get(event_type, []) + _listeners.get("*", [])
    )

    for handler in targets:
        try:
            handler(event_type, enriched)
        except Exception:
            logger.exception(
                "event_bus: handler %s raised an exception for event '%s'",
                getattr(handler, "__name__", repr(handler)),
                event_type,
            )
