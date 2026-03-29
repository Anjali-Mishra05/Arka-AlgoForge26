from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from utils import automations as automation_service
from utils.auth import get_current_user, is_admin

router = APIRouter(prefix="/automations", tags=["automations"])


class AutomationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=64)
    description: str = ""
    enabled: bool = True
    scope: Dict[str, Any] = Field(default_factory=dict)
    schedule: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)


class AutomationUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    type: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    scope: Optional[Dict[str, Any]] = None
    schedule: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


class AutomationToggleRequest(BaseModel):
    enabled: bool


class AutomationRunRequest(BaseModel):
    input: Dict[str, Any] = Field(default_factory=dict)


@router.get("")
async def list_automations(_: str = Depends(is_admin)):
    return automation_service.list_automations()


@router.post("")
async def create_automation(
    body: AutomationCreateRequest,
    current_user: dict = Depends(get_current_user),
    _: str = Depends(is_admin),
):
    if body.type not in automation_service.AUTOMATION_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported automation type")
    try:
        return automation_service.create_automation(body.model_dump(), current_user.get("email", "admin"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{automation_id}")
async def update_automation(automation_id: str, body: AutomationUpdateRequest, _: str = Depends(is_admin)):
    try:
        automation = automation_service.update_automation(automation_id, body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    return automation


@router.post("/{automation_id}/toggle")
async def toggle_automation(automation_id: str, body: AutomationToggleRequest, _: str = Depends(is_admin)):
    automation = automation_service.toggle_automation(automation_id, body.enabled)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    return automation


@router.post("/{automation_id}/run")
async def run_automation(
    automation_id: str,
    body: AutomationRunRequest,
    current_user: dict = Depends(get_current_user),
    _: str = Depends(is_admin),
):
    try:
        return automation_service.run_automation(automation_id, body.input, current_user.get("email", "admin"))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs")
async def recent_runs(limit: int = 20, automation_id: Optional[str] = None, _: str = Depends(is_admin)):
    return automation_service.list_recent_runs(limit=limit, automation_id=automation_id)
