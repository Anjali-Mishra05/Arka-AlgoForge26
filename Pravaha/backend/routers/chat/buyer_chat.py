"""
Public buyer-facing chat endpoint — no authentication required.
Buyers access this via a shared proposal link and can ask questions
about the proposal content. The admin sees all buyer interactions.
"""
from datetime import datetime
from html import unescape
import re

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from utils.chatbot import ChatBot
from utils.database import APP_DB_NAME, Database
from utils.hubspot import sync_buyer_to_crm

router = APIRouter(
    prefix="/proposal",
    tags=["proposal"],
)

# In-memory store for buyer chatbot sessions (keyed by proposal_id:session_id)
buyer_bots: dict = {}


class BuyerChatRequest(BaseModel):
    buyer_name: str
    buyer_email: str
    message: str
    session_id: str


class ProposalViewRequest(BaseModel):
    viewer_session: str | None = None
    referrer: str | None = None


class SectionDwellRequest(BaseModel):
    viewer_session: str
    sections: dict[str, int]  # section_id -> seconds since last beacon
    page_total_seconds: int = 0


def _strip_html(html_content: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(html_content or ""))).strip()


def _proposal_context(proposal: dict, session_id: str) -> str:
    proposal_text = proposal.get("markdown_content") or _strip_html(proposal.get("html_content", ""))
    documents = proposal.get("documents_used") or []
    session_history = next(
        (session for session in proposal.get("buyer_sessions", []) if session.get("session_id") == session_id),
        None,
    )

    context_parts = [
        f"Proposal ID: {proposal.get('proposal_id', '')}",
        f"Title: {proposal.get('title') or 'Shared proposal'}",
        f"Documents used: {', '.join(documents) if documents else 'Not specified'}",
    ]
    if proposal_text:
        context_parts.append(f"Proposal content:\n{proposal_text[:5000]}")
    if session_history and session_history.get("messages"):
        recent_turns = []
        for message in session_history["messages"][-6:]:
            role = "Buyer" if message.get("role") == "user" else "Assistant"
            content = str(message.get("content") or "").strip()
            if content:
                recent_turns.append(f"{role}: {content}")
        if recent_turns:
            context_parts.append("Conversation so far:\n" + "\n".join(recent_turns))
    return "\n\n".join(part for part in context_parts if part)


def _viewer_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None
    return request.client.host if request.client else None


@router.post("/{proposal_id}/chat")
async def buyer_chat(proposal_id: str, body: BuyerChatRequest):
    """
    No-auth endpoint. Buyers chat about the proposal.
    Stores the conversation in the proposal's buyer_sessions.
    """
    db = Database(APP_DB_NAME)

    # Verify proposal exists
    proposal = db.get_proposal_by_id(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    buyer_sessions = proposal.get("buyer_sessions") or []
    is_first_session = not any(session.get("session_id") == body.session_id for session in buyer_sessions)

    # Fire notification for admin on first buyer engagement
    if is_first_session:
        try:
            title_text = proposal.get("title") or proposal_id[:12]
            db.create_notification(
                notification_type="buyer_engagement",
                title=f"New buyer on \"{title_text}\"",
                message=f"{body.buyer_name} ({body.buyer_email}) started chatting about your proposal.",
                metadata={
                    "proposal_id": proposal_id,
                    "buyer_name": body.buyer_name,
                    "buyer_email": body.buyer_email,
                    "session_id": body.session_id,
                },
            )
        except Exception:
            pass  # never block the buyer flow

    # Retrieve or create a buyer bot for this session
    bot_key = f"{proposal_id}:{body.session_id}"
    if bot_key not in buyer_bots:
        buyer_bots[bot_key] = ChatBot(role="user")

    bot = buyer_bots[bot_key]

    # Store buyer question
    db.add_buyer_message(
        proposal_id=proposal_id,
        session_id=body.session_id,
        buyer_name=body.buyer_name,
        buyer_email=body.buyer_email,
        role="user",
        content=body.message,
    )

    if is_first_session:
        try:
            sync_result = sync_buyer_to_crm(
                proposal.get("created_by", "admin"),
                proposal_id,
                body.buyer_name,
                body.buyer_email,
                1,
            )
            if sync_result.get("status") == "synced":
                db.proposals_col.update_one(
                    {"proposal_id": proposal_id, "buyer_sessions.session_id": body.session_id},
                    {
                        "$set": {
                            "buyer_sessions.$.hubspot_contact_id": sync_result.get("contact_id"),
                            "buyer_sessions.$.hubspot_deal_id": sync_result.get("deal_id"),
                            "buyer_sessions.$.hubspot_synced_at": datetime.utcnow(),
                            "buyer_sessions.$.hubspot_sync_status": "synced",
                        }
                    },
                )
        except Exception:
            pass

    document_data = _proposal_context(proposal, body.session_id)

    # Get AI response
    ai_response = bot.invoke(
        text=body.message,
        document_data=document_data[:5000],
        proposal_context=document_data[:5000],
        include_all_proposals=False,
        persist_session=False,
    )

    # Store AI response
    db.add_buyer_message(
        proposal_id=proposal_id,
        session_id=body.session_id,
        buyer_name=body.buyer_name,
        buyer_email=body.buyer_email,
        role="assistant",
        content=ai_response,
    )

    return {"response": ai_response, "session_id": body.session_id}


@router.post("/{proposal_id}/view")
async def record_view(proposal_id: str, request: Request, body: ProposalViewRequest | None = None):
    """Track when a buyer opens the proposal."""
    db = Database(APP_DB_NAME)
    db.increment_proposal_view(
        proposal_id,
        viewer_session=body.viewer_session if body else None,
        viewer_ip=_viewer_ip(request),
        referrer=(body.referrer if body and body.referrer else request.headers.get("referer")),
    )
    # Fire notification on proposal view
    try:
        proposal = db.get_proposal_by_id(proposal_id)
        title_text = (proposal.get("title") if proposal else None) or proposal_id[:12]
        db.create_notification(
            notification_type="proposal_view",
            title=f"Proposal viewed: \"{title_text}\"",
            message=f"Someone opened your proposal link.",
            metadata={
                "proposal_id": proposal_id,
                "referrer": body.referrer if body else request.headers.get("referer"),
            },
        )
    except Exception:
        pass
    return {"status": "recorded"}


@router.post("/{proposal_id}/section_dwell")
async def record_section_dwell(proposal_id: str, body: SectionDwellRequest):
    """
    No-auth endpoint. The buyer's browser sends periodic beacons with
    per-section dwell times (seconds). These are accumulated in MongoDB
    and feed the engagement scoring engine.
    """
    db = Database(APP_DB_NAME)

    # Verify proposal exists
    proposal = db.get_proposal_by_id(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if not body.sections and body.page_total_seconds <= 0:
        return {"status": "skipped"}

    # Read previous cumulative page seconds for this session (for minute-boundary check)
    prev_doc = db.get_section_dwell_by_session(proposal_id, body.viewer_session)
    prev_total = (prev_doc or {}).get("page_total_seconds", 0)

    # Store the dwell data (atomic increment)
    db.upsert_section_dwell(
        proposal_id=proposal_id,
        viewer_session=body.viewer_session,
        sections=body.sections,
        page_total_seconds=body.page_total_seconds,
    )

    # Feed engagement scoring: emit one event per new full minute on page
    new_total = prev_total + body.page_total_seconds
    prev_minutes = prev_total // 60
    new_minutes = new_total // 60

    if new_minutes > prev_minutes:
        from utils.engagement import record_buyer_event

        for _ in range(new_minutes - prev_minutes):
            record_buyer_event(
                proposal_id,
                "time_on_page_minute",
                extra={"viewer_session": body.viewer_session},
            )

    return {"status": "recorded", "page_total_seconds": new_total}


@router.get("/{proposal_id}")
async def get_proposal_public(proposal_id: str):
    """Return the proposal HTML for the public viewer."""
    db = Database(APP_DB_NAME)
    proposal = db.get_proposal_by_id(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    onboarding = db.get_onboarding(proposal.get("created_by", "")) or {}
    return {
        "proposal_id": proposal_id,
        "html_content": proposal.get("html_content", ""),
        "created_at": proposal.get("created_at"),
        "title": proposal.get("title"),
        "brand": {
            "company_name": onboarding.get("company_name") or "Pravaha",
            "company_description": onboarding.get("company_description"),
            "website": onboarding.get("website"),
            "watermark_text": "Pravaha",
        },
    }
