from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
import os

from bson import ObjectId
from pymongo import ReturnDocument

from utils.database import APP_DB_NAME, Database
from utils.chatbot import ChatBot
from utils.vectorbase import PDFProcessor
from utils.bulkEmailSend import BulkEmailSender
from utils.call import _build_objection_summary
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


AUTOMATION_TYPES = {
    "summarize_transcript",
    "draft_proposal",
    "prepare_crm_note",
    "trigger_reminder",
    "manager_daily_brief",
}

DEFAULT_INTERVAL_MINUTES = 60
DEFAULT_RETRY_LIMIT = 3
DEFAULT_RETRY_BACKOFF_MINUTES = 15
CUSTOMER_FACING_AUTOMATION_TYPES = {"trigger_reminder"}


def _db() -> Database:
    return Database(APP_DB_NAME)


def _automations_collection():
    return _db().db["automations"]


def _runs_collection():
    return _db().db["automation_runs"]


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(doc)
    data.pop("_id", None)
    return _serialize_value(data)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items() if key != "_id"}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    return value


def _normalize_schedule(schedule: Optional[Dict[str, Any]], now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.utcnow()
    payload = dict(schedule or {})
    raw_mode = payload.get("mode") or payload.get("type") or payload.get("trigger") or payload.get("frequency")
    has_interval_fields = any(
        key in payload for key in ("interval_minutes", "every_minutes", "interval_hours", "every_hours", "interval")
    )
    mode = str(raw_mode or ("interval" if has_interval_fields else "manual")).strip().lower()
    if mode in {"hourly", "hours", "interval_hours"}:
        mode = "interval"
    if mode not in {"manual", "interval"}:
        raise ValueError("Unsupported schedule mode. Only manual and interval schedules are supported.")

    interval_value = (
        payload.get("interval_minutes")
        or payload.get("every_minutes")
        or (
            int(payload.get("interval_hours") or payload.get("every_hours") or payload.get("interval") or 0) * 60
            if payload.get("interval_hours") or payload.get("every_hours") or payload.get("interval")
            else None
        )
        or DEFAULT_INTERVAL_MINUTES
    )
    interval_minutes = int(interval_value)
    next_run_at = payload.get("next_run_at")
    if isinstance(next_run_at, str):
        try:
            next_run_at = datetime.fromisoformat(next_run_at)
        except ValueError:
            next_run_at = None
    if mode == "interval" and next_run_at is None:
        next_run_at = now + timedelta(minutes=max(1, interval_minutes))
    return {
        **payload,
        "mode": mode,
        "interval_minutes": max(1, interval_minutes),
        "next_run_at": next_run_at,
    }


def _normalize_config(automation_type: str, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = dict(config or {})
    payload.setdefault("retry_limit", DEFAULT_RETRY_LIMIT)
    payload.setdefault("retry_backoff_minutes", DEFAULT_RETRY_BACKOFF_MINUTES)
    if automation_type in CUSTOMER_FACING_AUTOMATION_TYPES:
        payload.setdefault("review_required", True)
    else:
        payload.setdefault("review_required", False)
    return payload


def _next_run_for_schedule(schedule: Dict[str, Any], from_time: Optional[datetime] = None) -> Optional[datetime]:
    mode = schedule.get("mode", "manual")
    if mode != "interval":
        return None
    base = from_time or datetime.utcnow()
    interval_minutes = int(schedule.get("interval_minutes") or DEFAULT_INTERVAL_MINUTES)
    return base + timedelta(minutes=max(1, interval_minutes))


def _safe_error_text(error: Optional[str]) -> Optional[str]:
    if not error:
        return None
    return error[:1000]


def list_automations() -> List[Dict[str, Any]]:
    ensure_default_automations()
    items = list(_automations_collection().find({}, {"_id": 0}).sort("updated_at", -1))
    normalized: List[Dict[str, Any]] = []
    for item in items:
        schedule = item.get("schedule")
        if not schedule:
            normalized.append(item)
            continue
        try:
            item["schedule"] = _normalize_schedule(schedule)
        except ValueError:
            item["runtime_status"] = item.get("runtime_status") or "unsupported_schedule"
            item["next_run_at"] = None
        normalized.append(item)
    return normalized


def create_automation(payload: Dict[str, Any], created_by: str) -> Dict[str, Any]:
    now = datetime.utcnow()
    schedule = _normalize_schedule(payload.get("schedule"), now=now)
    config = _normalize_config(payload["type"], payload.get("config"))
    automation = {
        "automation_id": str(uuid4()),
        "name": payload["name"],
        "type": payload["type"],
        "description": payload.get("description", ""),
        "enabled": payload.get("enabled", True),
        "scope": payload.get("scope", {}),
        "schedule": schedule,
        "config": config,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "last_run_at": None,
        "last_run_status": None,
        "last_error": None,
        "retry_count": 0,
        "runtime_status": "idle",
        "next_run_at": schedule.get("next_run_at"),
        "dead_lettered_at": None,
    }
    _automations_collection().insert_one(automation)
    return _serialize(automation)


def get_automation(automation_id: str) -> Optional[Dict[str, Any]]:
    return _automations_collection().find_one({"automation_id": automation_id}, {"_id": 0})


def update_automation(automation_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    update = {key: value for key, value in payload.items() if value is not None}
    if update:
        existing = get_automation(automation_id)
        if not existing:
            return None
        if "schedule" in update:
            update["schedule"] = _normalize_schedule(update["schedule"])
            update["next_run_at"] = update["schedule"].get("next_run_at")
        if "config" in update:
            update["config"] = _normalize_config(existing.get("type", ""), update["config"])
        update["updated_at"] = datetime.utcnow()
        _automations_collection().update_one({"automation_id": automation_id}, {"$set": update})
    return get_automation(automation_id)


def toggle_automation(automation_id: str, enabled: bool) -> Optional[Dict[str, Any]]:
    current = get_automation(automation_id)
    if not current:
        return None
    schedule = _normalize_schedule(current.get("schedule"))
    next_run_at = _next_run_for_schedule(schedule) if enabled else None
    _automations_collection().update_one(
        {"automation_id": automation_id},
        {
            "$set": {
                "enabled": enabled,
                "updated_at": datetime.utcnow(),
                "runtime_status": "idle" if enabled else "paused",
                "next_run_at": next_run_at,
                "retry_count": 0 if enabled else current.get("retry_count", 0),
                "dead_lettered_at": None if enabled else current.get("dead_lettered_at"),
            }
        },
    )
    return get_automation(automation_id)


def ensure_default_automations() -> None:
    now = datetime.utcnow()
    defaults = [
        {
            "name": "Stale Proposal Follow-up",
            "type": "trigger_reminder",
            "description": "Review or send follow-ups for stale proposals on a recurring interval.",
            "enabled": False,
            "scope": {},
            "schedule": _normalize_schedule({"mode": "interval", "interval_minutes": 60}, now=now),
            "config": _normalize_config("trigger_reminder", {"review_required": True, "retry_limit": 2}),
        },
        {
            "name": "Manager Daily Brief",
            "type": "manager_daily_brief",
            "description": "Generate a recurring manager brief from recent proposals, calls, syncs, and email activity.",
            "enabled": False,
            "scope": {},
            "schedule": _normalize_schedule({"mode": "interval", "interval_minutes": 1440}, now=now),
            "config": _normalize_config("manager_daily_brief", {"review_required": False, "retry_limit": 2}),
        },
    ]

    for item in defaults:
        _automations_collection().update_one(
            {"name": item["name"]},
            {
                "$setOnInsert": {
                    "automation_id": str(uuid4()),
                    "created_at": now,
                    "last_run_at": None,
                    "last_run_status": None,
                    "last_error": None,
                    "retry_count": 0,
                    "runtime_status": "idle" if item["enabled"] else "paused",
                    "dead_lettered_at": None,
                    **item,
                    "next_run_at": item["schedule"].get("next_run_at"),
                }
            },
            upsert=True,
        )


def _build_result(automation: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute automation and return real results based on type."""
    automation_type = automation.get("type")

    if automation_type == "summarize_transcript":
        return _run_summarize_transcript(automation, input_data)
    elif automation_type == "draft_proposal":
        return _run_draft_proposal(automation, input_data)
    elif automation_type == "prepare_crm_note":
        return _run_prepare_crm_note(automation, input_data)
    elif automation_type == "trigger_reminder":
        return _run_trigger_reminder(automation, input_data)
    elif automation_type == "manager_daily_brief":
        return _run_manager_daily_brief(automation, input_data)

    return {"message": "Automation executed", "input": input_data}


def _run_summarize_transcript(automation: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize a call transcript using Groq LLM."""
    try:
        # Get transcript from input or most recent call
        transcript = input_data.get("transcript")
        call_id = input_data.get("call_id")

        if not transcript and call_id:
            call_data = _db().get_call_by_id(call_id)
            if call_data:
                transcript = call_data.get("transcript", "")

        if not transcript:
            return {"error": "No transcript available"}

        # Use Groq to generate structured summary
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
        )

        prompt = PromptTemplate(
            input_variables=["transcript"],
            template="""Analyze this sales call transcript and provide a structured summary with:
1. Key topics discussed (list 3-5 bullet points)
2. Objections raised (if any)
3. Buying signals (if any)
4. Next steps agreed
5. Overall sentiment (positive/neutral/negative)

Transcript:
{transcript}

Provide a clear, concise summary."""
        )

        chain = LLMChain(llm=llm, prompt=prompt)
        summary = chain.invoke({"transcript": transcript})
        summary = summary.get("text", str(summary)) if isinstance(summary, dict) else str(summary)

        return {
            "summary": summary,
            "call_id": call_id,
            "status": "completed"
        }
    except Exception as e:
        return {"error": str(e)}


def _run_draft_proposal(automation: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a new proposal draft using existing logic."""
    try:
        from routers.admin.generate_proposal import generate_proposal as gen_prop

        # Call the existing proposal generation logic
        result = gen_prop()

        return {
            "proposal_id": result.get("proposal_id"),
            "status": "generated",
            "title": result.get("title"),
            "created_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


def _run_prepare_crm_note(automation: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare a CRM note from recent call activity."""
    try:
        call_id = input_data.get("call_id")

        if not call_id:
            return {"error": "call_id required"}

        # Fetch call summary
        call_data = _db().get_call_by_id(call_id)
        if not call_data:
            return {"error": "Call not found"}

        # Build CRM note using existing logic
        from utils.hubspot import build_crm_note_body

        objections = _build_objection_summary(call_data)

        note_body = build_crm_note_body(
            call_summary=call_data,
            objection_summary=objections,
        )

        return {
            "crm_note": note_body,
            "call_id": call_id,
            "status": "prepared"
        }
    except Exception as e:
        return {"error": str(e)}


def _run_trigger_reminder(automation: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send follow-up emails for stale proposals."""
    try:
        # Get stale proposals
        automation_db = _db()
        stale_hours = int(automation.get("config", {}).get("stale_hours") or 48)
        stale_proposals = automation_db.get_stale_proposals(stale_hours=stale_hours)

        if not stale_proposals:
            return {"reminders_sent": 0, "proposal_ids": []}

        # Initialize email sender
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_username = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")

        from_email = os.getenv("SMTP_FROM_EMAIL", smtp_username)
        sender = BulkEmailSender(smtp_server, smtp_port, smtp_username, smtp_password, from_email)
        sender.connect()

        reminders_sent = 0
        proposal_ids = []

        # Send reminders for each stale proposal
        for proposal in stale_proposals:
            proposal_id = proposal.get("proposal_id")

            # Get buyer emails from sessions
            buyer_sessions = proposal.get("buyer_sessions", [])
            if not buyer_sessions:
                continue

            for session in buyer_sessions:
                buyer_email = session.get("buyer_email")
                buyer_name = session.get("buyer_name", "Prospect")

                if not buyer_email:
                    continue

                # Compose follow-up email
                subject = f"Follow-up: {proposal.get('title', 'Your Proposal')}"
                body = f"""Hi {buyer_name},

I wanted to follow up on the proposal we shared with you.

Do you have any questions or would you like to schedule a time to discuss further?

Looking forward to hearing from you!

Best regards,
Sales Team"""

                # Send email
                try:
                    sender.send_email(buyer_email, subject, body)
                    reminders_sent += 1
                    proposal_ids.append(proposal_id)

                    # Mark follow-up sent
                    automation_db.mark_followup_sent(proposal_id)
                except Exception as email_error:
                    pass  # Log but continue with other proposals

        try:
            sender.disconnect()
        except Exception:
            pass

        return {
            "reminders_sent": reminders_sent,
            "proposal_ids": proposal_ids,
            "status": "completed"
        }
    except Exception as e:
        return {"error": str(e)}


def _run_manager_daily_brief(automation: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate and save a manager's daily brief."""
    try:
        # Replicate daily_brief endpoint logic
        automation_db = _db()
        proposals = automation_db.get_all_proposals_list()
        calls = automation_db.get_recent_call_insights(limit=20)
        sync_log = automation_db.get_sync_log(limit=20)
        email_data = automation_db.get_email_insights(limit=10)

        proposal_views = sum(int(p.get("views", 0) or 0) for p in proposals)
        buyer_sessions = sum(len(p.get("buyer_sessions", []) or []) for p in proposals)

        # Summarize recent calls
        from routers.admin.intelligence import _summarise_calls
        recent_call_signals = _summarise_calls(calls)
        objection_labels = [item.get("label", "") for item in recent_call_signals.get("top_objections", []) if item.get("label")]
        signal_labels = [item.get("label", "") for item in recent_call_signals.get("top_signals", []) if item.get("label")]

        # Identify high-signal proposals
        high_signal_proposals = sorted(
            proposals,
            key=lambda proposal: (
                int(proposal.get("views", 0) or 0),
                len(proposal.get("buyer_sessions", []) or []),
            ),
            reverse=True,
        )[:5]

        # Build top risks and opportunities
        top_risks = []
        if "pricing" in objection_labels:
            top_risks.append("Pricing objections are recurring in recent calls.")
        if "timeline" in objection_labels:
            top_risks.append("Implementation timeline questions need a clearer answer.")
        if "competitor" in objection_labels:
            top_risks.append("Competitive comparisons are active and need tighter positioning.")
        if not top_risks:
            top_risks.append("No major objection cluster surfaced in the recent call set.")

        top_opportunities = []
        if buyer_sessions > 0:
            top_opportunities.append("Buyer chat is active and can be mined for proposal improvements.")
        if proposal_views > 0:
            top_opportunities.append("Proposal engagement is happening and can be turned into follow-ups.")
        if "roi" in signal_labels:
            top_opportunities.append("ROI language is showing up as a buying signal.")
        if not top_opportunities:
            top_opportunities.append("No strong upside signal surfaced yet; keep outbound motion active.")

        # Build summary briefs
        briefs = [
            f"Tracked {len(proposals)} proposals with {proposal_views} total views and {buyer_sessions} buyer sessions.",
            f"Recent call themes: {', '.join(objection_labels[:3]) or 'none'}.",
        ]
        if sync_log:
            successful_syncs = sum(1 for item in sync_log if item.get("status") == "success")
            briefs.append(f"{successful_syncs} recent sync events completed successfully.")
        if email_data.get("total_campaigns"):
            email_themes = [t["theme"] for t in email_data.get("themes", [])[:3]]
            briefs.append(
                f"{email_data['total_campaigns']} email campaigns sent ({email_data['total_sent']} emails). "
                f"Top themes: {', '.join(email_themes) or 'general outreach'}."
            )

        brief_data = {
            "manager_id": input_data.get("user_id", "manager"),
            "summary": " ".join(briefs),
            "top_risks": top_risks,
            "top_opportunities": top_opportunities,
            "reps_needing_attention": [],
            "deals_most_likely_to_move": [
                {
                    "proposal_id": proposal.get("proposal_id"),
                    "views": proposal.get("views", 0),
                    "buyer_sessions": len(proposal.get("buyer_sessions", []) or []),
                }
                for proposal in high_signal_proposals
            ],
            "recent_call_signals": recent_call_signals,
            "email_insights": email_data,
            "sync_events": sync_log,
            "generated_at": datetime.utcnow(),
        }

        # Save to database
        automation_db.save_daily_brief(
            scope_key=input_data.get("user_id", "manager"),
            brief_type="manager_daily_brief",
            content=brief_data,
            metadata={"source": "automation", "automation_type": automation.get("type")},
        )

        return {
            "brief_id": str(uuid4()),
            "date": datetime.utcnow().date().isoformat(),
            "summary": brief_data.get("summary"),
            "status": "completed"
        }
    except Exception as e:
        return {"error": str(e)}


def _claim_automation(
    automation_id: str,
    now: datetime,
    runner: str,
    *,
    require_enabled: bool = True,
) -> Optional[Dict[str, Any]]:
    query: Dict[str, Any] = {
        "automation_id": automation_id,
        "$or": [{"runtime_status": {"$exists": False}}, {"runtime_status": {"$ne": "running"}}],
    }
    if require_enabled:
        query["enabled"] = True

    return _automations_collection().find_one_and_update(
        query,
        {
            "$set": {
                "runtime_status": "running",
                "claimed_at": now,
                "claimed_by": runner,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )


def _build_run_doc(
    automation: Dict[str, Any],
    input_data: Dict[str, Any],
    output: Dict[str, Any],
    status: str,
    triggered_by: str,
    started_at: datetime,
    completed_at: datetime,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "run_id": str(uuid4()),
        "automation_id": automation.get("automation_id"),
        "automation_name": automation.get("name"),
        "automation_type": automation.get("type"),
        "input": input_data,
        "output": output,
        "status": status,
        "error": _safe_error_text(error),
        "triggered_by": triggered_by,
        "started_at": started_at,
        "completed_at": completed_at,
        "finished_at": completed_at,
    }


def _finalize_run(
    automation: Dict[str, Any],
    run_doc: Dict[str, Any],
    *,
    success: bool,
    now: datetime,
    error: Optional[str] = None,
    preserve_retry_state: bool = False,
) -> Dict[str, Any]:
    schedule = _normalize_schedule(automation.get("schedule"))
    config = _normalize_config(automation.get("type", ""), automation.get("config"))
    retry_count = int(automation.get("retry_count") or 0)
    retry_limit = int(config.get("retry_limit") or DEFAULT_RETRY_LIMIT)
    next_run_at: Optional[datetime] = None
    runtime_status = "idle"
    dead_lettered_at = automation.get("dead_lettered_at")
    review_required = bool(config.get("review_required")) and not success and preserve_retry_state
    review_required_reason = None
    dead_lettered = False
    dead_letter_reason = None

    if success:
        retry_count = 0
        dead_lettered_at = None
        next_run_at = _next_run_for_schedule(schedule, now)
    elif preserve_retry_state:
        next_run_at = _next_run_for_schedule(schedule, now)
        review_required_reason = (
            run_doc.get("output", {}).get("message")
            if isinstance(run_doc.get("output"), dict)
            else "Scheduled run skipped pending review."
        )
    else:
        retry_count += 1
        if retry_count > retry_limit:
            runtime_status = "dead_letter"
            dead_lettered_at = now
            next_run_at = None
            dead_lettered = True
            dead_letter_reason = _safe_error_text(error) or "Retry limit exceeded."
        else:
            backoff = int(config.get("retry_backoff_minutes") or DEFAULT_RETRY_BACKOFF_MINUTES)
            next_run_at = now + timedelta(minutes=max(1, backoff) * retry_count)

    run_doc["retry_count"] = retry_count
    run_doc["max_retries"] = retry_limit
    run_doc["review_required"] = review_required
    run_doc["review_required_reason"] = review_required_reason
    run_doc["dead_lettered"] = dead_lettered
    run_doc["dead_letter_reason"] = dead_letter_reason
    _runs_collection().insert_one(run_doc)
    _automations_collection().update_one(
        {"automation_id": automation.get("automation_id")},
        {
            "$set": {
                "last_run_at": now,
                "last_run_status": run_doc["status"],
                "last_error": _safe_error_text(error),
                "updated_at": now,
                "runtime_status": runtime_status,
                "retry_count": retry_count,
                "next_run_at": next_run_at,
                "dead_lettered_at": dead_lettered_at,
                "claimed_at": None,
                "claimed_by": None,
            }
        },
    )
    return _serialize(run_doc)


def run_automation(automation_id: str, input_data: Dict[str, Any], triggered_by: str) -> Dict[str, Any]:
    automation = get_automation(automation_id)
    if not automation:
        raise ValueError("Automation not found")

    started_at = datetime.utcnow()
    claimed = _claim_automation(automation_id, started_at, triggered_by, require_enabled=False)
    if not claimed:
        raise ValueError("Automation is already running")

    try:
        output = _build_result(claimed, input_data)
        error = output.get("error") if isinstance(output, dict) else None
        status = "failed" if error else "success"
        completed_at = datetime.utcnow()
        run_doc = _build_run_doc(
            claimed,
            input_data,
            output if isinstance(output, dict) else {"output": output},
            status,
            triggered_by,
            started_at,
            completed_at,
            error=error,
        )
        return _finalize_run(claimed, run_doc, success=(status == "success"), now=completed_at, error=error)
    except Exception as exc:  # pragma: no cover
        completed_at = datetime.utcnow()
        run_doc = _build_run_doc(
            claimed,
            input_data,
            {"error": str(exc)},
            "failed",
            triggered_by,
            started_at,
            completed_at,
            error=str(exc),
        )
        return _finalize_run(claimed, run_doc, success=False, now=completed_at, error=str(exc))


def run_due_automations_once(triggered_by: str = "scheduler") -> List[Dict[str, Any]]:
    now = datetime.utcnow()
    results: List[Dict[str, Any]] = []
    due_automations = list(
        _automations_collection().find(
            {
                "enabled": True,
                "schedule.mode": "interval",
                "next_run_at": {"$ne": None, "$lte": now},
                "$or": [{"runtime_status": {"$exists": False}}, {"runtime_status": {"$ne": "running"}}],
            },
            {"_id": 0},
        )
    )

    for automation in due_automations:
        claimed = _claim_automation(automation.get("automation_id"), now, triggered_by)
        if not claimed:
            continue

        config = _normalize_config(claimed.get("type", ""), claimed.get("config"))
        started_at = datetime.utcnow()
        if config.get("review_required"):
            completed_at = datetime.utcnow()
            output = {
                "message": "Scheduled run skipped because review is required before executing this automation.",
                "review_required": True,
            }
            run_doc = _build_run_doc(
                claimed,
                {},
                output,
                "pending_review",
                triggered_by,
                started_at,
                completed_at,
            )
            results.append(
                _finalize_run(
                    claimed,
                    run_doc,
                    success=False,
                    now=completed_at,
                    error=None,
                    preserve_retry_state=True,
                )
            )
            continue

        try:
            output = _build_result(claimed, {})
            error = output.get("error") if isinstance(output, dict) else None
            status = "failed" if error else "success"
            completed_at = datetime.utcnow()
            run_doc = _build_run_doc(
                claimed,
                {},
                output if isinstance(output, dict) else {"output": output},
                status,
                triggered_by,
                started_at,
                completed_at,
                error=error,
            )
            results.append(
                _finalize_run(claimed, run_doc, success=(status == "success"), now=completed_at, error=error)
            )
        except Exception as exc:  # pragma: no cover
            completed_at = datetime.utcnow()
            run_doc = _build_run_doc(
                claimed,
                {},
                {"error": str(exc)},
                "failed",
                triggered_by,
                started_at,
                completed_at,
                error=str(exc),
            )
            results.append(_finalize_run(claimed, run_doc, success=False, now=completed_at, error=str(exc)))

    return results


def list_recent_runs(limit: int = 20, automation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {}
    if automation_id:
        query["automation_id"] = automation_id
    runs = list(_runs_collection().find(query, {"_id": 0}).sort("started_at", -1).limit(limit))
    return [_serialize(run) for run in runs]
