"""
mcp_orchestrator.py — MCP Rules Engine (IF event + conditions → THEN actions).

The "brain" of the Zapier integration. Users define rules via the admin UI;
this engine evaluates them when events fire and dispatches actions.

Architecture:
  event_bus.emit(event_type, payload)
      ↓
  mcp_orchestrator._evaluate_rules(event_type, payload)
      ↓ (for each matching rule)
  _dispatch_action(action, payload)
      ↓
  fire Zapier webhook  OR  run internal action
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.database import APP_DB_NAME, Database
from utils.event_bus import EVENTS, on

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Condition evaluator
# ---------------------------------------------------------------------------

def _evaluate_conditions(conditions: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """Return True if all conditions match the payload.

    Supported condition operators:
        score_gte    → payload["score"] >= value
        score_lte    → payload["score"] <= value
        tier         → payload["tier"] == value
        tier_in      → payload["tier"] in [value, ...]
        field_equals → payload[field] == value
        field_contains → value in str(payload.get(field, ""))
    """
    if not conditions:
        return True  # No conditions = always match

    for key, value in conditions.items():
        if key == "score_gte":
            if payload.get("score", 0) < value:
                return False
        elif key == "score_lte":
            if payload.get("score", 0) > value:
                return False
        elif key == "tier":
            if payload.get("tier") != value:
                return False
        elif key == "tier_in":
            if payload.get("tier") not in (value or []):
                return False
        elif key.startswith("field_equals:"):
            field = key.split(":", 1)[1]
            if payload.get(field) != value:
                return False
        elif key.startswith("field_contains:"):
            field = key.split(":", 1)[1]
            if value not in str(payload.get(field, "")):
                return False
    return True


# ---------------------------------------------------------------------------
# Action dispatcher
# ---------------------------------------------------------------------------

def _dispatch_action(action: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single rule action. Returns a result dict."""
    action_type = action.get("type")

    if action_type == "zapier_webhook":
        webhook_id = action.get("webhook_id")
        if not webhook_id:
            return {"type": action_type, "status": "skipped", "reason": "no webhook_id"}

        from utils.zapier_webhooks import fire_webhooks
        app_db = Database(APP_DB_NAME)
        wh = app_db.get_zapier_webhook(webhook_id)
        if not wh:
            return {"type": action_type, "status": "skipped", "reason": "webhook not found"}

        results = fire_webhooks(wh["event_type"], payload)
        status = "success" if any(r.get("status") == "success" for r in results) else "failed"
        return {"type": action_type, "webhook_id": webhook_id, "status": status}

    elif action_type == "internal":
        internal_action = action.get("action")
        params = action.get("params", {})
        return _run_internal_action(internal_action, params, payload)

    else:
        return {"type": action_type, "status": "skipped", "reason": f"unknown action type: {action_type}"}


def _run_internal_action(
    action_name: Optional[str],
    params: Dict[str, Any],
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Dispatch built-in internal actions."""
    if action_name == "log":
        logger.info("mcp_orchestrator [internal/log]: %s | payload keys: %s", params, list(payload.keys()))
        return {"type": "internal", "action": "log", "status": "success"}

    # More internal actions can be added here (send_email, create_task, etc.)
    return {"type": "internal", "action": action_name, "status": "skipped", "reason": "not implemented"}


# ---------------------------------------------------------------------------
# Rule evaluation
# ---------------------------------------------------------------------------

def evaluate_rules(event_type: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Find and execute all enabled rules matching *event_type*.

    Logs execution to sync_log. Returns list of execution results.
    """
    app_db = Database(APP_DB_NAME)
    rules = app_db.list_automation_rules()
    results: List[Dict[str, Any]] = []

    matching_rules = [
        r for r in rules
        if r.get("enabled", True) and r.get("event_type") == event_type
    ]

    for rule in matching_rules:
        rule_id = rule.get("rule_id", "?")
        conditions = rule.get("conditions", {})

        if not _evaluate_conditions(conditions, payload):
            logger.debug("mcp_orchestrator: rule '%s' conditions not met", rule_id)
            continue

        logger.info("mcp_orchestrator: rule '%s' matched event '%s'", rule.get("name"), event_type)
        action_results = []
        for action in rule.get("actions", []):
            try:
                result = _dispatch_action(action, payload)
                action_results.append(result)
            except Exception:
                logger.exception("mcp_orchestrator: action dispatch error in rule %s", rule_id)
                action_results.append({"status": "error"})

        execution = {
            "rule_id": rule_id,
            "rule_name": rule.get("name"),
            "event_type": event_type,
            "actions_executed": len(action_results),
            "results": action_results,
            "executed_at": datetime.utcnow().isoformat(),
        }
        results.append(execution)

        # Log to sync_log
        try:
            app_db.log_sync_event(
                event=f"rule:{rule_id}",
                provider="mcp_orchestrator",
                entity_id=event_type,
                status="success",
                data=execution,
                error=None,
            )
        except Exception:
            pass

    return results


# ---------------------------------------------------------------------------
# Register as event_bus listener
# ---------------------------------------------------------------------------

def _orchestrator_listener(event_type: str, payload: Dict[str, Any]) -> None:
    evaluate_rules(event_type, payload)


def register_orchestrator() -> None:
    """Call once at startup to connect event_bus → MCP orchestrator."""
    on("*", _orchestrator_listener)
    logger.info("mcp_orchestrator: registered wildcard listener")


# ---------------------------------------------------------------------------
# Rule CRUD helpers (used by the admin API)
# ---------------------------------------------------------------------------

def create_rule(
    name: str,
    event_type: str,
    conditions: Dict[str, Any],
    actions: List[Dict[str, Any]],
    created_by: str,
    enabled: bool = True,
) -> Dict[str, Any]:
    if event_type not in EVENTS:
        raise ValueError(f"Unknown event type: {event_type}")

    rule = {
        "rule_id": str(uuid.uuid4()),
        "name": name,
        "event_type": event_type,
        "conditions": conditions,
        "actions": actions,
        "enabled": enabled,
        "created_by": created_by,
    }
    app_db = Database(APP_DB_NAME)
    return app_db.create_automation_rule(rule)
