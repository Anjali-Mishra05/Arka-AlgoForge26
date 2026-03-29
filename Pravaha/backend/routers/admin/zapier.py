"""
admin/zapier.py — Zapier integration admin API.

Manages:
- Zapier API key storage
- Outbound webhook CRUD + test
- Automation rules (IF→THEN)
- Inbound data from Zapier (no JWT — API key auth)
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from utils.auth import get_current_user, is_admin
from utils.database import APP_DB_NAME, Database
from utils.event_bus import EVENTS, EVENT_DESCRIPTIONS
from utils.zapier_webhooks import fire_webhooks, test_webhook
from utils.mcp_orchestrator import create_rule

router = APIRouter(prefix="/zapier", tags=["admin"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ApiKeyRequest(BaseModel):
    api_key: str = Field(min_length=8)


class WebhookCreateRequest(BaseModel):
    event_type: str
    webhook_url: str = Field(min_length=10)
    label: str = Field(max_length=120)
    enabled: bool = True


class WebhookUpdateRequest(BaseModel):
    webhook_url: Optional[str] = None
    label: Optional[str] = None
    enabled: Optional[bool] = None


class RuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    event_type: str
    conditions: Dict[str, Any] = Field(default_factory=dict)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    enabled: bool = True


class RuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    event_type: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    enabled: Optional[bool] = None


class InboundRequest(BaseModel):
    action: str
    data: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db() -> Database:
    return Database(APP_DB_NAME)


def _require_user(current_user=Depends(get_current_user)) -> str:
    return current_user["username"]


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------

@router.put("/api-key", dependencies=[Depends(is_admin)])
async def save_api_key(
    body: ApiKeyRequest,
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    _get_db().save_zapier_api_key(current_user["username"], body.api_key)
    return {"status": "saved"}


@router.delete("/api-key", dependencies=[Depends(is_admin)])
async def delete_api_key(current_user=Depends(get_current_user)) -> Dict[str, Any]:
    deleted = _get_db().delete_zapier_api_key(current_user["username"])
    return {"status": "deleted" if deleted else "not_found"}


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/status", dependencies=[Depends(is_admin)])
async def get_status(current_user=Depends(get_current_user)) -> Dict[str, Any]:
    app_db = _get_db()
    user_id = current_user["username"]
    api_key = app_db.get_zapier_api_key(user_id)
    webhooks = app_db.list_zapier_webhooks(user_id)
    rules = app_db.list_automation_rules(user_id)

    last_activity = None
    sync_entries = list(app_db.sync_log.find(
        {"provider": {"$in": ["zapier", "mcp_orchestrator"]}},
        {"_id": 0, "created_at": 1},
    ).sort("created_at", -1).limit(1))
    if sync_entries and sync_entries[0].get("created_at"):
        last_activity = sync_entries[0]["created_at"].isoformat()

    return {
        "api_key_configured": bool(api_key),
        "webhook_count": len(webhooks),
        "rule_count": len(rules),
        "last_activity": last_activity,
    }


# ---------------------------------------------------------------------------
# Event types reference
# ---------------------------------------------------------------------------

@router.get("/events")
async def list_events() -> Dict[str, Any]:
    return {
        "events": [
            {"event_type": et, "description": EVENT_DESCRIPTIONS.get(et, "")}
            for et in sorted(EVENTS)
        ]
    }


# ---------------------------------------------------------------------------
# Webhook CRUD
# ---------------------------------------------------------------------------

@router.post("/webhooks", dependencies=[Depends(is_admin)])
async def create_webhook(
    body: WebhookCreateRequest,
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    if body.event_type not in EVENTS:
        raise HTTPException(status_code=422, detail=f"Unknown event_type: {body.event_type}")

    wh = _get_db().create_zapier_webhook(
        user_id=current_user["username"],
        event_type=body.event_type,
        webhook_url=body.webhook_url,
        label=body.label,
        enabled=body.enabled,
    )
    return wh


@router.get("/webhooks", dependencies=[Depends(is_admin)])
async def list_webhooks(current_user=Depends(get_current_user)) -> Dict[str, Any]:
    webhooks = _get_db().list_zapier_webhooks(current_user["username"])
    return {"webhooks": webhooks}


@router.patch("/webhooks/{webhook_id}", dependencies=[Depends(is_admin)])
async def update_webhook(webhook_id: str, body: WebhookUpdateRequest) -> Dict[str, Any]:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = _get_db().update_zapier_webhook(webhook_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "updated"}


@router.delete("/webhooks/{webhook_id}", dependencies=[Depends(is_admin)])
async def delete_webhook(webhook_id: str) -> Dict[str, Any]:
    deleted = _get_db().delete_zapier_webhook(webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "deleted"}


@router.post("/webhooks/{webhook_id}/test", dependencies=[Depends(is_admin)])
async def test_webhook_endpoint(webhook_id: str) -> Dict[str, Any]:
    result = test_webhook(webhook_id)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Automation rules
# ---------------------------------------------------------------------------

@router.post("/rules", dependencies=[Depends(is_admin)])
async def create_rule_endpoint(
    body: RuleCreateRequest,
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    try:
        rule = create_rule(
            name=body.name,
            event_type=body.event_type,
            conditions=body.conditions,
            actions=body.actions,
            created_by=current_user["username"],
            enabled=body.enabled,
        )
        return rule
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/rules", dependencies=[Depends(is_admin)])
async def list_rules(current_user=Depends(get_current_user)) -> Dict[str, Any]:
    rules = _get_db().list_automation_rules(current_user["username"])
    return {"rules": rules}


@router.patch("/rules/{rule_id}", dependencies=[Depends(is_admin)])
async def update_rule(rule_id: str, body: RuleUpdateRequest) -> Dict[str, Any]:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updated = _get_db().update_automation_rule(rule_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "updated"}


@router.delete("/rules/{rule_id}", dependencies=[Depends(is_admin)])
async def delete_rule(rule_id: str) -> Dict[str, Any]:
    deleted = _get_db().delete_automation_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Inbound webhook (from Zapier → Pravaha, API key auth — no JWT)
# ---------------------------------------------------------------------------

@router.post("/inbound")
async def inbound_webhook(
    body: InboundRequest,
    x_zapier_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """Receive data from Zapier. Authenticated via x-zapier-token header.

    Supported actions:
        - log            → store payload in sync_log (testing/debug)
        - trigger_event  → emit an event_bus event with provided payload
    """
    if not x_zapier_token:
        raise HTTPException(status_code=401, detail="Missing x-zapier-token header")

    # Validate token against any stored Zapier API key
    app_db = _get_db()
    # Find any user whose stored api_key matches
    integration = app_db.db["integrations"].find_one(
        {"provider": "zapier", "api_key": x_zapier_token}
    )
    if not integration:
        raise HTTPException(status_code=401, detail="Invalid zapier token")

    action = body.action
    data = body.data

    if action == "log":
        app_db.log_sync_event(
            event="zapier_inbound:log",
            provider="zapier_inbound",
            entity_id="inbound",
            status="success",
            data=data,
            error=None,
        )
        return {"status": "logged"}

    elif action == "trigger_event":
        event_type = data.get("event_type")
        if not event_type or event_type not in EVENTS:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid event_type. Must be one of: {sorted(EVENTS)}"
            )
        from utils.event_bus import emit
        emit(event_type, {**data, "source": "zapier_inbound"})
        return {"status": "emitted", "event_type": event_type}

    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown action '{action}'. Supported: log, trigger_event"
        )
