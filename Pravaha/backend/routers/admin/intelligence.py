"""
Admin intelligence endpoints for actionable sales ops summaries.
"""

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from utils.auth import get_current_user, is_admin
from utils.database import APP_DB_NAME, Database

router = APIRouter(prefix="/intelligence", tags=["admin-intelligence"])


def _db() -> Database:
    return Database(APP_DB_NAME)


def _normalise_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _extract_signals(text: str) -> List[str]:
    text_lower = text.lower()
    signals: List[str] = []

    signal_map = {
        "pricing": ["price", "pricing", "budget", "expensive", "cost"],
        "timeline": ["timeline", "time", "soon", "delay", "implementation"],
        "competitor": ["competitor", "alternative", "existing vendor", "already use"],
        "integration": ["integration", "crm", "hubspot", "salesforce", "api"],
        "security": ["security", "compliance", "gdpr", "privacy"],
        "roi": ["roi", "return", "value", "impact", "outcome"],
        "onboarding": ["onboarding", "setup", "training", "adoption"],
    }

    for label, tokens in signal_map.items():
        if any(token in text_lower for token in tokens):
            signals.append(label)

    return signals


def _summarise_calls(calls: List[Dict[str, Any]]) -> Dict[str, Any]:
    objection_counter: Counter[str] = Counter()
    signal_counter: Counter[str] = Counter()
    risk_counter: Counter[str] = Counter()
    recent_highlights: List[str] = []

    for call in calls:
        summary = _normalise_text(call.get("summary"))
        transcript = _normalise_text(call.get("transcript"))
        text = f"{summary}\n{transcript}"
        for signal in _extract_signals(text):
            signal_counter[signal] += 1
            if signal in {"pricing", "timeline", "competitor", "integration", "security"}:
                objection_counter[signal] += 1
        risk_level = _normalise_text(call.get("risk_level") or call.get("objection_summary", {}).get("risk_level"))
        if risk_level:
            risk_counter[risk_level.lower()] += 1
        if summary:
            recent_highlights.append(summary[:220])

    return {
        "top_signals": [{"label": item, "count": count} for item, count in signal_counter.most_common(5)],
        "top_objections": [{"label": item, "count": count} for item, count in objection_counter.most_common(5)],
        "risk_breakdown": dict(risk_counter),
        "recent_highlights": recent_highlights[:5],
    }


def _proposal_title(proposal: Dict[str, Any]) -> str:
    return proposal.get("title") or proposal.get("proposal_id") or "Untitled proposal"


def _count_proposal_signals_since(proposals: List[Dict[str, Any]], since: Optional[datetime]) -> Dict[str, int]:
    if not since:
        return {"views": 0, "buyer_questions": 0, "buyer_sessions": 0}

    views = 0
    buyer_questions = 0
    buyer_sessions = 0
    for proposal in proposals:
        for view in proposal.get("view_log", []) or []:
            viewed_at = view.get("viewed_at")
            if isinstance(viewed_at, datetime) and viewed_at > since:
                views += 1
        for session in proposal.get("buyer_sessions", []) or []:
            started_at = session.get("started_at")
            if isinstance(started_at, datetime) and started_at > since:
                buyer_sessions += 1
            for message in session.get("messages", []) or []:
                occurred_at = message.get("timestamp")
                if message.get("role") == "user" and isinstance(occurred_at, datetime) and occurred_at > since:
                    buyer_questions += 1
    return {
        "views": views,
        "buyer_questions": buyer_questions,
        "buyer_sessions": buyer_sessions,
    }


def _count_calls_since(calls: List[Dict[str, Any]], since: Optional[datetime]) -> int:
    if not since:
        return 0
    return sum(1 for call in calls if isinstance(call.get("created_at"), datetime) and call.get("created_at") > since)


def _count_sync_success_since(sync_log: List[Dict[str, Any]], since: Optional[datetime]) -> int:
    if not since:
        return 0
    return sum(
        1
        for item in sync_log
        if item.get("status") == "success" and isinstance(item.get("created_at"), datetime) and item.get("created_at") > since
    )


def _normalise_action_document(
    action_doc: Dict[str, Any],
    proposals: List[Dict[str, Any]],
    calls: List[Dict[str, Any]],
    sync_log: List[Dict[str, Any]],
) -> Dict[str, Any]:
    payload = dict(action_doc.get("action") or {})
    events = action_doc.get("events", []) or []
    last_event = events[-1] if events else None
    tracking_anchor = None
    if last_event and isinstance(last_event.get("created_at"), datetime):
        tracking_anchor = last_event.get("created_at")
    elif isinstance(action_doc.get("created_at"), datetime):
        tracking_anchor = action_doc.get("created_at")

    payload["action_id"] = action_doc.get("action_id")
    payload["events"] = events
    payload["tracking"] = {
        "actions_taken": len(events),
        "last_event": last_event,
        "follow_on_signals": {
            **_count_proposal_signals_since(proposals, tracking_anchor),
            "calls": _count_calls_since(calls, tracking_anchor),
            "sync_success": _count_sync_success_since(sync_log, tracking_anchor),
        },
    }
    return payload


def _extract_recent_leads(proposals: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    leads: List[Dict[str, Any]] = []
    for proposal in proposals:
        for session in proposal.get("buyer_sessions", []) or []:
            messages = session.get("messages", []) or []
            last_buyer_message = next(
                (message.get("content", "") for message in reversed(messages) if message.get("role") == "user"),
                "",
            )
            last_active = session.get("last_active") or session.get("started_at") or proposal.get("created_at")
            leads.append(
                {
                    "proposal_id": proposal.get("proposal_id"),
                    "proposal_title": _proposal_title(proposal),
                    "buyer_name": session.get("buyer_name") or "Unknown buyer",
                    "buyer_email": session.get("buyer_email") or "",
                    "question_count": sum(1 for message in messages if message.get("role") == "user"),
                    "last_message": last_buyer_message[:180],
                    "last_active": last_active,
                    "views": int(proposal.get("views", 0) or 0),
                }
            )

    leads.sort(
        key=lambda item: (
            item.get("last_active") or datetime.min,
            item.get("question_count", 0),
            item.get("views", 0),
        ),
        reverse=True,
    )
    return leads[:limit]


def _brief_item(title: str, detail: str, tone: str, count: Optional[int] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"title": title, "detail": detail, "tone": tone}
    if count is not None:
        payload["count"] = count
    return payload


def _build_daily_brief(manager_id: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]:
    db = _db()
    scope_key = manager_id or "manager"
    if not refresh:
        cached = db.get_daily_brief(scope_key, "manager_daily_brief")
        if cached:
            return cached.get("content", {})

    proposals = db.get_all_proposals_list()
    calls = db.get_recent_call_insights(limit=20)
    sync_log = db.get_sync_log(limit=20)
    email_data = db.get_email_insights(limit=10)

    proposal_views = sum(int(proposal.get("views", 0) or 0) for proposal in proposals)
    buyer_sessions = sum(len(proposal.get("buyer_sessions", []) or []) for proposal in proposals)
    call_signals = _summarise_calls(calls)
    recent_leads = _extract_recent_leads(proposals, limit=5)
    sync_success_count = sum(1 for item in sync_log if item.get("status") == "success")

    top_risks: List[Dict[str, Any]] = []
    for objection in call_signals["top_objections"]:
        label = objection["label"]
        count = int(objection["count"])
        if label == "pricing":
            top_risks.append(
                _brief_item(
                    "Pricing objections are recurring",
                    f"Recent call summaries referenced pricing or budget concerns in {count} conversations.",
                    "risk",
                    count,
                )
            )
        elif label == "timeline":
            top_risks.append(
                _brief_item(
                    "Timeline questions need a tighter answer",
                    f"Implementation timing surfaced in {count} recent calls and may be stalling next steps.",
                    "risk",
                    count,
                )
            )
        elif label == "competitor":
            top_risks.append(
                _brief_item(
                    "Competitive pressure is active",
                    f"Prospects referenced other vendors in {count} recent conversations.",
                    "risk",
                    count,
                )
            )
    if not top_risks:
        top_risks.append(
            _brief_item(
                "No dominant objection cluster",
                "Recent call summaries did not surface a repeated risk pattern that needs urgent intervention.",
                "neutral",
            )
        )

    top_opportunities: List[Dict[str, Any]] = []
    if buyer_sessions:
        top_opportunities.append(
            _brief_item(
                "Buyer chat is producing signal",
                f"{buyer_sessions} buyer sessions are active across shared proposals and can drive targeted follow-ups.",
                "opportunity",
                buyer_sessions,
            )
        )
    if proposal_views:
        top_opportunities.append(
            _brief_item(
                "Proposal engagement is live",
                f"Buyers generated {proposal_views} tracked proposal views, which is enough to justify sharper follow-up sequencing.",
                "opportunity",
                proposal_views,
            )
        )
    roi_signal = next((item for item in call_signals["top_signals"] if item["label"] == "roi"), None)
    if roi_signal:
        top_opportunities.append(
            _brief_item(
                "ROI language is showing up",
                f"Value and ROI signals appeared in {roi_signal['count']} recent conversations.",
                "opportunity",
                int(roi_signal["count"]),
            )
        )
    if sync_success_count:
        top_opportunities.append(
            _brief_item(
                "CRM sync is landing cleanly",
                f"{sync_success_count} recent sync events completed successfully, so follow-ups can rely on CRM state.",
                "opportunity",
                sync_success_count,
            )
        )
    if not top_opportunities:
        top_opportunities.append(
            _brief_item(
                "Outbound motion needs more signal",
                "No strong buyer or call signal has surfaced yet, so keep proposal and outreach velocity moving.",
                "neutral",
            )
        )

    rep_alerts: List[Dict[str, Any]] = []
    for lead in recent_leads[:3]:
        rep_alerts.append(
            _brief_item(
                f"{lead['buyer_name']} reopened {lead['proposal_title']}",
                f"{lead['question_count']} buyer questions and {lead['views']} views. Latest note: {lead['last_message'] or 'No recent buyer message.'}",
                "neutral",
                int(lead["question_count"]),
            )
        )
    if not rep_alerts and calls:
        rep_alerts.append(
            _brief_item(
                "Review recent call summaries",
                "Call activity exists, but there are no buyer engagement alerts yet. Review summaries for manual follow-up.",
                "neutral",
            )
        )

    summary_parts = [
        f"Tracked {len(proposals)} proposals with {proposal_views} views and {buyer_sessions} buyer sessions.",
        f"Processed {len(calls)} recent calls with top objections: {', '.join(item['label'] for item in call_signals['top_objections'][:3]) or 'none'}.",
    ]
    if email_data.get("total_campaigns"):
        summary_parts.append(
            f"Email activity covered {email_data['total_campaigns']} campaigns and {email_data['total_sent']} messages."
        )
    if sync_log:
        summary_parts.append(f"{sync_success_count} recent CRM sync events completed successfully.")

    stats = [
        {"label": "Tracked Proposals", "value": len(proposals)},
        {"label": "Proposal Views", "value": proposal_views},
        {"label": "Buyer Sessions", "value": buyer_sessions},
        {"label": "Recent Calls", "value": len(calls)},
    ]

    share_text = "\n".join(
        [
            "Pravaha Manager Daily Brief",
            f"Generated: {datetime.utcnow().isoformat()}",
            "",
            "Summary:",
            " ".join(summary_parts),
            "",
            "Top Risks:",
            *[f"- {item['title']}: {item['detail']}" for item in top_risks],
            "",
            "Top Opportunities:",
            *[f"- {item['title']}: {item['detail']}" for item in top_opportunities],
        ]
    )

    brief = {
        "manager_id": manager_id,
        "summary": " ".join(summary_parts),
        "top_risks": top_risks,
        "top_opportunities": top_opportunities,
        "rep_alerts": rep_alerts,
        "stats": stats,
        "recent_call_signals": call_signals,
        "recent_leads": recent_leads,
        "email_insights": email_data,
        "sync_events": sync_log,
        "generated_at": datetime.utcnow(),
        "share_text": share_text,
        "export_filename": f"pravaha-daily-brief-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt",
    }
    db.save_daily_brief(scope_key, "manager_daily_brief", brief, metadata={"manager_id": manager_id})
    db.save_agent_action(
        agent="intelligence",
        action="daily_brief_generated",
        output_data={"scope_key": scope_key, "summary": brief["summary"]},
        user_id=scope_key,
        metadata={"risk_count": len(top_risks), "opportunity_count": len(top_opportunities)},
    )
    return brief


def _build_next_best_action(rep_id: Optional[str] = None, refresh: bool = False) -> Dict[str, Any]:
    db = _db()
    scope_key = rep_id or "manager"
    proposals = db.get_all_proposals_list()
    calls = db.get_recent_call_insights(limit=10)
    sync_log = db.get_sync_log(limit=20)

    if not refresh:
        cached = db.get_next_best_action(scope_key)
        if cached:
            return _normalise_action_document(cached, proposals, calls, sync_log)

    signals = _summarise_calls(calls)
    recent_leads = _extract_recent_leads(proposals, limit=5)

    recommendation: Dict[str, Any]
    pricing_signal = next((item for item in signals["top_objections"] if item["label"] == "pricing"), None)
    timeline_signal = next((item for item in signals["top_objections"] if item["label"] == "timeline"), None)
    competitor_signal = next((item for item in signals["top_objections"] if item["label"] == "competitor"), None)
    roi_signal = next((item for item in signals["top_signals"] if item["label"] == "roi"), None)

    if pricing_signal:
        recommendation = {
            "action": "Review active proposals and send a pricing clarification follow-up",
            "why": f"Pricing objections appeared in {pricing_signal['count']} recent call summaries.",
            "urgency": "high",
            "confidence": 0.89,
            "source": "call_objections",
            "cta_label": "Open proposals",
            "cta_href": "/dashboard/proposals",
        }
    elif timeline_signal:
        recommendation = {
            "action": "Send an implementation timeline and onboarding plan",
            "why": f"Timeline risk appeared in {timeline_signal['count']} recent conversations and needs a clearer answer.",
            "urgency": "high",
            "confidence": 0.84,
            "source": "call_objections",
            "cta_label": "Open call summaries",
            "cta_href": "/dashboard/voice",
        }
    elif recent_leads:
        hottest_lead = recent_leads[0]
        recommendation = {
            "action": f"Follow up with {hottest_lead['buyer_name']} on {hottest_lead['proposal_title']}",
            "why": f"The buyer reopened the proposal and asked {hottest_lead['question_count']} questions.",
            "urgency": "medium",
            "confidence": 0.8,
            "source": "buyer_engagement",
            "cta_label": "Review proposal engagement",
            "cta_href": "/dashboard/proposals",
        }
    elif competitor_signal:
        recommendation = {
            "action": "Prepare a competitor differentiation note for the next follow-up",
            "why": f"Competitive references showed up in {competitor_signal['count']} recent conversations.",
            "urgency": "high",
            "confidence": 0.83,
            "source": "call_objections",
            "cta_label": "Open sales coach",
        "cta_href": "/chat",
        }
    elif roi_signal:
        recommendation = {
            "action": "Send ROI proof points and a concrete case study",
            "why": f"ROI language showed up in {roi_signal['count']} recent buyer conversations.",
            "urgency": "medium",
            "confidence": 0.78,
            "source": "buying_signals",
            "cta_label": "Open proposals",
            "cta_href": "/dashboard/proposals",
        }
    else:
        recommendation = {
            "action": "Schedule the next decision-step follow-up",
            "why": "No urgent blocker surfaced, so the best move is to keep active deals warm and time-bound.",
            "urgency": "medium",
            "confidence": 0.65,
            "source": "baseline",
            "cta_label": "Open dashboard",
            "cta_href": "/dashboard",
        }

    recommendation["rep_id"] = rep_id
    recommendation["proposal_count"] = len(proposals)
    recommendation["total_views"] = sum(int(proposal.get("views", 0) or 0) for proposal in proposals)
    recommendation["total_buyer_sessions"] = sum(len(proposal.get("buyer_sessions", []) or []) for proposal in proposals)
    recommendation["signals"] = signals
    recommendation["recent_leads"] = recent_leads[:3]
    recommendation["generated_at"] = datetime.utcnow()
    recommendation["copy_text"] = f"{recommendation['action']}\n\nWhy: {recommendation['why']}"

    db.save_next_best_action(scope_key, recommendation, source="intelligence")
    db.save_agent_action(
        agent="intelligence",
        action="next_best_action_generated",
        input_data={"rep_id": rep_id},
        output_data={"action": recommendation.get("action"), "why": recommendation.get("why")},
        user_id=scope_key,
        metadata={"source": recommendation.get("source"), "urgency": recommendation.get("urgency")},
    )
    stored = db.get_next_best_action(scope_key)
    if stored:
        return _normalise_action_document(stored, proposals, calls, sync_log)
    return recommendation


def track_next_best_action(rep_id: Optional[str], event: str, notes: str = "", metadata: Optional[Dict[str, Any]] = None):
    db = _db()
    scope_key = rep_id or "manager"
    proposals = db.get_all_proposals_list()
    calls = db.get_recent_call_insights(limit=10)
    sync_log = db.get_sync_log(limit=20)
    tracked = db.track_next_best_action_event(scope_key, event, notes=notes, metadata=metadata or {})
    if not tracked:
        _build_next_best_action(scope_key, refresh=True)
        tracked = db.track_next_best_action_event(scope_key, event, notes=notes, metadata=metadata or {})
    if not tracked:
        return None
    db.save_agent_action(
        agent="intelligence",
        action=f"next_best_action_{event}",
        input_data=metadata or {},
        output_data={"notes": notes},
        user_id=scope_key,
        metadata={"rep_id": rep_id},
    )
    return _normalise_action_document(tracked, proposals, calls, sync_log)


class NextBestActionTrackRequest(BaseModel):
    rep_id: Optional[str] = None
    event: str
    notes: str = ""
    metadata: Dict[str, Any] = {}


@router.get("/email_insights")
async def email_insights(_: str = Depends(is_admin)):
    """Return aggregated insights from recent email campaigns for cross-channel use."""
    return _db().get_email_insights(limit=20)


@router.get("/next_best_action")
async def next_best_action(rep_id: Optional[str] = None, refresh: bool = False, _: str = Depends(is_admin)):
    return _build_next_best_action(rep_id, refresh=refresh)


@router.post("/next_best_action/track")
async def track_next_best_action_route(body: NextBestActionTrackRequest, _: str = Depends(is_admin)):
    tracked = track_next_best_action(body.rep_id, body.event, body.notes, body.metadata)
    return tracked or {"status": "missing"}


@router.get("/daily_brief")
async def daily_brief(manager_id: Optional[str] = None, refresh: bool = False, _: str = Depends(is_admin)):
    return _build_daily_brief(manager_id, refresh=refresh)


@router.get("/daily_brief/export")
async def export_daily_brief(manager_id: Optional[str] = None, refresh: bool = False, _: str = Depends(is_admin)):
    brief = _build_daily_brief(manager_id, refresh=refresh)
    return PlainTextResponse(
        brief["share_text"],
        headers={"Content-Disposition": f'attachment; filename="{brief["export_filename"]}"'},
    )


@router.get("/agent_actions")
async def agent_actions(limit: int = 20, _: str = Depends(is_admin)):
    return _db().get_agent_actions(limit=limit, agent="intelligence")
