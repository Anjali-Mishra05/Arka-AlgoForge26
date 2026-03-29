import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import dotenv
import requests
from fastapi import HTTPException

from .database import APP_DB_NAME, Database
from .hubspot import build_call_crm_payload, sync_call_to_crm

dotenv.load_dotenv()

VAPI_BASE_URL = "https://api.vapi.ai"
DEFAULT_VAPI_MODEL_PROVIDER = os.getenv("VAPI_MODEL_PROVIDER", "groq")
DEFAULT_VAPI_MODEL_NAME = os.getenv("VAPI_MODEL_NAME", "llama-3.3-70b-versatile")
DEFAULT_VAPI_VOICE_PROVIDER = os.getenv("VAPI_VOICE_PROVIDER", "azure")
DEFAULT_VAPI_VOICE_ID = os.getenv("VAPI_VOICE_ID", "emma")

OBJECTION_RULES = [
    {
        "type": "pricing",
        "label": "Pricing or budget",
        "keywords": ["price", "pricing", "cost", "budget", "expensive", "too much", "too costly", "roi"],
    },
    {
        "type": "timeline",
        "label": "Timeline or urgency",
        "keywords": ["timeline", "timing", "when", "later", "busy", "not now", "next quarter", "delay"],
    },
    {
        "type": "competitor",
        "label": "Competitor comparison",
        "keywords": ["competitor", "alternative", "switch", "already use", "currently use", "vendor", "provider"],
    },
    {
        "type": "features",
        "label": "Feature or integration gap",
        "keywords": ["feature", "integration", "missing", "does it support", "works with", "api", "connect"],
    },
    {
        "type": "approval",
        "label": "Approval or stakeholder review",
        "keywords": ["approval", "approve", "boss", "manager", "legal", "finance", "stakeholder", "sign off"],
    },
    {
        "type": "trust",
        "label": "Security or trust",
        "keywords": ["security", "trust", "compliance", "risk", "safe", "private", "confidential", "gdpr"],
    },
]

BUYING_SIGNAL_RULES = [
    {
        "type": "interest",
        "label": "Active interest",
        "keywords": ["interested", "sounds good", "sounds great", "makes sense", "we need this", "let's do it"],
    },
    {
        "type": "next_step",
        "label": "Next step requested",
        "keywords": ["send", "share", "follow up", "demo", "proposal", "quote", "trial", "pilot"],
    },
    {
        "type": "priority",
        "label": "Business priority",
        "keywords": ["important", "priority", "urgent", "must have", "high value", "top of mind"],
    },
]


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _collect_evidence(text: str, keywords: list[str]) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    lower = cleaned.lower()
    for keyword in keywords:
        if keyword in lower:
            index = lower.find(keyword)
            start = max(0, index - 70)
            end = min(len(cleaned), index + len(keyword) + 90)
            return cleaned[start:end].strip()
    return ""


def _extract_matches(text: str, rules: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    matches = []
    lower = (text or "").lower()
    for rule in rules:
        evidence = _collect_evidence(text, rule["keywords"])
        if evidence or any(keyword in lower for keyword in rule["keywords"]):
            matches.append(
                {
                    "type": rule["type"],
                    "label": rule["label"],
                    "evidence": evidence or rule["keywords"][0],
                }
            )
    return matches


def _build_objection_summary(call: Dict[str, Any]) -> Dict[str, Any]:
    transcript = _clean_text(call.get("transcript") or "")
    summary = _clean_text(call.get("summary") or "")
    combined = " ".join([part for part in [summary, transcript] if part]).strip()
    objections = _extract_matches(combined, OBJECTION_RULES)
    buying_signals = _extract_matches(combined, BUYING_SIGNAL_RULES)

    questions = []
    for source in [summary, transcript]:
        for chunk in re.split(r"[.?!\n]", source or ""):
            chunk = _clean_text(chunk)
            if "?" in chunk or chunk.lower().startswith(("how", "what", "when", "where", "why", "which")):
                questions.append(chunk)
    questions = list(dict.fromkeys([q for q in questions if len(q) > 3]))[:6]

    risk_level = "low"
    if objections:
        risk_level = "high" if any(item["type"] in {"pricing", "competitor", "approval"} for item in objections) else "medium"
    elif not buying_signals:
        risk_level = "medium"

    action_items = []
    if any(item["type"] == "pricing" for item in objections):
        action_items.append("Send ROI proof and pricing breakdown.")
    if any(item["type"] == "competitor" for item in objections):
        action_items.append("Share differentiation against the named competitor.")
    if any(item["type"] == "timeline" for item in objections):
        action_items.append("Clarify implementation milestones and rollout plan.")
    if any(item["type"] == "approval" for item in objections):
        action_items.append("Prepare a short stakeholder-ready summary for approval.")
    if not action_items:
        action_items.append("Follow up with a concise recap and next-step confirmation.")

    recommended_next_step = action_items[0]
    if buying_signals and risk_level == "low":
        recommended_next_step = "Move the buyer to the next step with a demo or proposal."

    objection_labels = [item["label"] for item in objections]
    signal_labels = [item["label"] for item in buying_signals]
    return {
        "has_objection": bool(objections),
        "risk_level": risk_level,
        "objections": objections,
        "buying_signals": buying_signals,
        "questions": questions,
        "action_items": action_items,
        "recommended_next_step": recommended_next_step,
        "summary_text": summary,
        "objection_labels": objection_labels,
        "signal_labels": signal_labels,
        "crm_note_title": f"Call summary for {call.get('phone_number') or call.get('call_id') or 'unknown'}",
    }


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {os.getenv('VAPI_API_KEY')}",
        "Content-Type": "application/json",
    }


def _assistant_payload(system_prompt: str, context: str, webhook_url: str, webhook_secret: str | None) -> Dict[str, Any]:
    assistant = {
        "transcriber": {"provider": "deepgram"},
        "model": {
            "provider": DEFAULT_VAPI_MODEL_PROVIDER,
            "model": DEFAULT_VAPI_MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": f"{system_prompt}\n\nAdditional context:\n{context}".strip(),
                }
            ],
        },
        "voice": {
            "provider": DEFAULT_VAPI_VOICE_PROVIDER,
            "voiceId": DEFAULT_VAPI_VOICE_ID,
        },
        "firstMessage": "Hello, this is pravaha from Pravaha. How can I assist you today?",
        "endCallFunctionEnabled": True,
        "endCallMessage": "Happy to help! Goodbye!",
    }

    if webhook_secret:
        assistant["serverUrl"] = webhook_url
        assistant["serverUrlSecret"] = webhook_secret

    return assistant


def _normalise_summary(call: Dict[str, Any]) -> Dict[str, Any]:
    messages = call.get("messages") or []
    transcript_lines = []
    for message in messages:
        role = message.get("role", "unknown")
        text = message.get("message") or message.get("content") or ""
        if text:
            transcript_lines.append(f"{role}: {text}")

    summary = call.get("summary") or ""
    key_points = []
    if summary:
        key_points = [line.strip("- ").strip() for line in summary.splitlines() if line.strip()][:5]

    objection_summary = _build_objection_summary(call)
    crm_payload = build_call_crm_payload(
        {
            "call_id": call.get("id") or call.get("call_id"),
            "phone_number": (call.get("customer") or {}).get("number") or call.get("phone_number"),
            "summary": summary,
            "duration_seconds": call.get("duration") or call.get("durationSeconds") or 0,
            "transcript": "\n".join(transcript_lines),
        },
        objection_summary,
    )

    return {
        "call_id": call.get("id") or call.get("call_id"),
        "phone_number": (call.get("customer") or {}).get("number") or call.get("phone_number"),
        "customer": call.get("customer"),
        "status": call.get("status", "unknown"),
        "started_at": call.get("startedAt") or call.get("createdAt"),
        "ended_at": call.get("endedAt") or call.get("updatedAt"),
        "duration_seconds": call.get("duration") or call.get("durationSeconds") or 0,
        "summary": summary,
        "key_points": key_points,
        "next_steps": key_points[:3],
        "transcript": "\n".join(transcript_lines),
        "recording_url": call.get("recordingUrl"),
        "objection_summary": objection_summary,
        "crm_note": crm_payload["body"],
        "crm_note_title": crm_payload["subject"],
        "follow_up_actions": objection_summary.get("action_items", []),
        "buying_signals": objection_summary.get("buying_signals", []),
        "open_questions": objection_summary.get("questions", []),
        "risk_level": objection_summary.get("risk_level", "medium"),
        "recommended_next_step": objection_summary.get("recommended_next_step", ""),
        "raw": call,
    }


def handle_call(phone_number: str, name: str, system_prompt: str, context: str = "") -> Dict[str, Any]:
    # ── Validate Twilio credentials ──────────────────────────────────────────
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER", "").strip()

    if not twilio_sid or not twilio_token:
        raise HTTPException(
            status_code=400,
            detail=(
                "Twilio credentials are not configured. "
                "Add TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN to your .env file, "
                "then restart the backend."
            ),
        )
    if not twilio_number:
        raise HTTPException(
            status_code=400,
            detail="TWILIO_PHONE_NUMBER is not set in your .env file.",
        )

    # ── Validate phone number format (E.164: +<country><number>) ─────────────
    normalized = phone_number.strip()
    if not normalized.startswith("+"):
        normalized = "+" + normalized
    if not re.fullmatch(r"\+[1-9]\d{6,14}", normalized):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid phone number '{phone_number}'. "
                "Use E.164 format, e.g. +918269336982 for India or +12125551234 for US."
            ),
        )

    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    webhook_url = f"{api_base_url}/webhook/vapi"
    webhook_secret = os.getenv("VAPI_WEBHOOK_SECRET")

    payload = {
        "assistant": _assistant_payload(system_prompt, context, webhook_url, webhook_secret),
        "customer": {"number": normalized, "name": name},
        "phoneNumber": {
            "twilioAuthToken": twilio_token,
            "twilioAccountSid": twilio_sid,
            "twilioPhoneNumber": twilio_number,
        },
    }

    try:
        response = requests.post(f"{VAPI_BASE_URL}/call/phone", json=payload, headers=_headers(), timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        # Surface VAPI's error message instead of a raw 500
        try:
            vapi_detail = exc.response.json()
            msg = vapi_detail.get("message") or vapi_detail.get("error") or str(vapi_detail)
        except Exception:
            msg = str(exc)
        raise HTTPException(status_code=502, detail=f"VAPI error: {msg}") from exc
    except requests.exceptions.RequestException as exc:
        raise HTTPException(status_code=503, detail=f"Could not reach VAPI: {exc}") from exc

    data = response.json()

    return {
        "call_id": data.get("id") or data.get("call_id"),
        "phone_number": normalized,
        "status": data.get("status", "initiated"),
        "started_at": data.get("createdAt"),
        "raw": data,
    }


def get_call_status(call_id: str) -> Dict[str, Any]:
    response = requests.get(f"{VAPI_BASE_URL}/call/{call_id}", headers={"Authorization": _headers()["Authorization"]}, timeout=30)
    response.raise_for_status()
    data = response.json()
    db = Database(APP_DB_NAME)
    live_doc = db.get_call_by_id(call_id) or {}
    return {
        "call_id": data.get("id") or call_id,
        "status": data.get("status", "unknown"),
        "phone_number": (data.get("customer") or {}).get("number"),
        "started_at": data.get("createdAt") or data.get("startedAt"),
        "ended_at": data.get("updatedAt") or data.get("endedAt"),
        "duration_seconds": data.get("duration") or data.get("durationSeconds") or 0,
        "live_transcript": live_doc.get("live_transcript", []),
        "last_transcript_at": live_doc.get("last_transcript_at"),
        "coaching_tip_count": len(db.get_coaching_tips_for_call(call_id)),
        "raw": data,
    }


def latest_summary(call_id: Optional[str] = None):
    if call_id:
        response = requests.get(f"{VAPI_BASE_URL}/call/{call_id}", headers={"Authorization": _headers()["Authorization"]}, timeout=30)
        response.raise_for_status()
        call = response.json()
        summary = _normalise_summary(call)
        if summary["summary"]:
            _persist_summary(summary)
        return summary

    response = requests.get(f"{VAPI_BASE_URL}/call", headers={"Authorization": _headers()["Authorization"]}, timeout=30)
    response.raise_for_status()
    calls = response.json()
    for call in calls:
        if "summary" in call and call.get("summary"):
            summary = _normalise_summary(call)
            _persist_summary(summary)
            return summary

    return {
        "call_id": None,
        "status": "not_found",
        "summary": "",
        "key_points": [],
        "next_steps": [],
        "transcript": "",
        "duration_seconds": 0,
        "objection_summary": {
            "has_objection": False,
            "risk_level": "low",
            "objections": [],
            "buying_signals": [],
            "questions": [],
            "action_items": [],
            "recommended_next_step": "",
            "summary_text": "",
            "objection_labels": [],
            "signal_labels": [],
            "crm_note_title": "",
        },
        "crm_note": "",
        "crm_note_title": "",
        "follow_up_actions": [],
        "buying_signals": [],
        "open_questions": [],
        "risk_level": "low",
        "recommended_next_step": "",
    }


def _persist_summary(summary: Dict[str, Any]) -> None:
    try:
        db = Database(APP_DB_NAME)
        db.save_call_summary(
            call_id=summary.get("call_id") or "",
            phone=summary.get("phone_number") or "",
            summary=summary.get("summary") or "",
            transcript=summary.get("transcript") or "",
            duration=summary.get("duration_seconds") or 0,
        )
        db.calls_col.update_one(
            {"call_id": summary.get("call_id") or ""},
            {
                "$set": {
                    "call_id": summary.get("call_id") or "",
                    "phone_number": summary.get("phone_number") or "",
                    "summary": summary.get("summary") or "",
                    "transcript": summary.get("transcript") or "",
                    "duration_seconds": summary.get("duration_seconds") or 0,
                    "key_points": summary.get("key_points") or [],
                    "next_steps": summary.get("next_steps") or [],
                    "objection_summary": summary.get("objection_summary") or {},
                    "crm_note": summary.get("crm_note") or "",
                    "crm_note_title": summary.get("crm_note_title") or "",
                    "follow_up_actions": summary.get("follow_up_actions") or [],
                    "buying_signals": summary.get("buying_signals") or [],
                    "open_questions": summary.get("open_questions") or [],
                    "risk_level": summary.get("risk_level") or "medium",
                    "recommended_next_step": summary.get("recommended_next_step") or "",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        if summary.get("summary") and summary.get("call_id"):
            sync_call_to_crm(
                None,
                summary.get("phone_number") or "",
                summary.get("summary") or "",
                "",
                summary.get("call_id") or "",
            )
    except Exception:
        pass


async def user_messages_latest():
    response = requests.get(f"{VAPI_BASE_URL}/call", headers={"Authorization": _headers()["Authorization"]}, timeout=30)

    if response.status_code == 200:
        res = response.json()
        user_msg = []
        for message in res[0]["messages"]:
            if message["role"] == "user":
                user_msg.append(message["message"])
        return user_msg
    return "Error!"


async def insert_user_message_db():
    db = Database(APP_DB_NAME)
    user_msg = await user_messages_latest()
    arr = []
    for msg in user_msg:
        arr.append({"user": "human", "message": msg})
    db.insert_call_chats({"sessions": arr})
