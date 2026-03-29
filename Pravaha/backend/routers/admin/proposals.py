"""
Admin endpoints for managing proposals and viewing buyer engagement.
"""
from collections import Counter, defaultdict
from datetime import datetime
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from utils.auth import is_admin, get_current_user, oauth2_scheme
from utils.database import APP_DB_NAME, Database

router = APIRouter(prefix="/proposals")


SECTION_KEYWORDS = {
    "pricing": ["price", "pricing", "cost", "budget", "fee", "fees", "expensive", "roi", "discount"],
    "timeline": ["timeline", "time", "deadline", "delivery", "implementation", "launch", "go live", "rollout"],
    "integration": ["integration", "api", "crm", "salesforce", "hubspot", "zapier", "connect", "sync"],
    "security": ["security", "compliance", "privacy", "gdpr", "dpdp", "risk", "encryption"],
    "onboarding": ["onboarding", "setup", "implementation", "training", "go live", "migration"],
    "support": ["support", "success", "sla", "service", "account manager", "help", "customer success"],
    "features": ["feature", "capability", "workflow", "automation", "reporting", "analytics"],
}


class SuggestionGenerateRequest(BaseModel):
    force: bool = Field(default=False, description="Regenerate suggestions even if cached suggestions exist.")


class SectionRegenerateRequest(BaseModel):
    section_name: str = Field(min_length=1, max_length=64)


def _proposal_doc(db: Database, proposal_id: str):
    proposal = db.get_proposal_by_id(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


def _question_texts(proposal: dict) -> list[str]:
    texts: list[str] = []
    for session in proposal.get("buyer_sessions", []):
        for message in session.get("messages", []):
            if message.get("role") == "user" and message.get("content"):
                texts.append(str(message["content"]).strip())
    return texts


def _normalize_section_name(section_name: str) -> str:
    return re.sub(r"\s+", " ", section_name.strip().lower())


def _detect_sections_from_questions(questions: list[str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for question in questions:
        lowered = question.lower()
        matched = False
        for section, keywords in SECTION_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                buckets[section].append(question)
                matched = True
        if not matched:
            buckets["general"].append(question)
    return buckets


def _build_section_copy(section_name: str, questions: list[str]) -> str:
    normalized = _normalize_section_name(section_name)
    theme_questions = questions[:5]
    if normalized == "pricing":
        return (
            "Pricing summary: clearly state implementation fees, subscription cost, and any optional services. "
            "Address value by linking cost to ROI and include a direct answer to budget objections. "
            f"Buyer concerns observed: {', '.join(theme_questions) if theme_questions else 'pricing clarity and value proof'}."
        )
    if normalized == "timeline":
        return (
            "Timeline summary: break delivery into discovery, setup, rollout, and first-value milestones. "
            "Show a realistic implementation calendar and call out dependencies up front. "
            f"Buyer concerns observed: {', '.join(theme_questions) if theme_questions else 'delivery timing and launch planning'}."
        )
    if normalized == "integration":
        return (
            "Integration summary: explain how Pravaha connects with the buyer's existing stack, the setup steps, and the systems supported. "
            "Call out CRM sync, data mapping, and technical support for implementation. "
            f"Buyer concerns observed: {', '.join(theme_questions) if theme_questions else 'connectivity, CRM sync, and API support'}."
        )
    if normalized == "security":
        return (
            "Security summary: outline data handling, access control, auditability, and compliance posture in plain language. "
            "Reduce risk concerns by naming safeguards and ownership boundaries explicitly. "
            f"Buyer concerns observed: {', '.join(theme_questions) if theme_questions else 'privacy, access, and compliance'}."
        )
    if normalized == "onboarding":
        return (
            "Onboarding summary: present the first 30 days as a guided rollout with clear owners, milestones, and training checkpoints. "
            "Make it obvious how fast the buyer can reach first value. "
            f"Buyer concerns observed: {', '.join(theme_questions) if theme_questions else 'setup, training, and adoption'}."
        )
    if normalized == "support":
        return (
            "Support summary: describe onboarding assistance, success coverage, response expectations, and escalation paths. "
            "Clarify who helps the buyer after go-live and how issues are handled. "
            f"Buyer concerns observed: {', '.join(theme_questions) if theme_questions else 'support coverage and escalation'}."
        )
    return (
        f"{section_name.title()} summary: tighten this section to answer the most common buyer questions directly. "
        "Use concise language, show outcomes, and reduce ambiguity around next steps. "
        f"Relevant buyer questions: {', '.join(theme_questions) if theme_questions else 'general buyer follow-up questions'}."
    )


def _extract_reasons_from_questions(questions: list[str], limit: int = 5) -> list[str]:
    reasons = []
    for question in questions:
        lowered = question.lower()
        if any(term in lowered for term in ["price", "cost", "budget", "fee"]):
            reasons.append("Buyer is pushing for pricing clarity and value justification.")
        elif any(term in lowered for term in ["timeline", "time", "launch", "deadline"]):
            reasons.append("Buyer wants a more concrete implementation timeline.")
        elif any(term in lowered for term in ["integrat", "crm", "api", "hubspot", "salesforce"]):
            reasons.append("Buyer needs clearer integration details.")
        elif any(term in lowered for term in ["security", "privacy", "compliance", "gdpr", "dpdp"]):
            reasons.append("Buyer wants stronger security and compliance language.")
        elif any(term in lowered for term in ["onboard", "setup", "train"]):
            reasons.append("Buyer needs a clearer onboarding and adoption path.")
        elif any(term in lowered for term in ["support", "help", "success", "sla"]):
            reasons.append("Buyer is looking for support coverage and escalation clarity.")
        else:
            reasons.append("Buyer question suggests the section should be more specific and outcome-focused.")
    deduped = []
    seen = set()
    for reason in reasons:
        if reason not in seen:
            deduped.append(reason)
            seen.add(reason)
    return deduped[:limit]


def _generate_suggestions_for_proposal(proposal: dict) -> list[dict]:
    questions = _question_texts(proposal)
    if not questions:
        return []

    buckets = _detect_sections_from_questions(questions)
    suggestions: list[dict] = []
    for section, section_questions in buckets.items():
        if section == "general" and len(section_questions) < 2:
            continue
        suggestions.append(
            {
                "suggestion_id": str(uuid.uuid4()),
                "section_name": section,
                "status": "open",
                "reason": "; ".join(_extract_reasons_from_questions(section_questions)),
                "source_questions": section_questions[:10],
                "suggested_copy": _build_section_copy(section, section_questions),
                "created_at": datetime.utcnow(),
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "suggestion_id": str(uuid.uuid4()),
                "section_name": "general",
                "status": "open",
                "reason": "No strong theme detected, but the proposal can still be tightened around repeated buyer questions.",
                "source_questions": questions[:10],
                "suggested_copy": _build_section_copy("general", questions),
                "created_at": datetime.utcnow(),
            }
        )
    return suggestions


def _store_revision_suggestions(db: Database, proposal_id: str, suggestions: list[dict]) -> list[dict]:
    if not suggestions:
        return []

    db.proposals_col.update_one(
        {"proposal_id": proposal_id},
        {
            "$set": {"revision_suggestions_updated_at": datetime.utcnow()},
            "$push": {"revision_suggestions": {"$each": suggestions}},
        },
    )
    return suggestions


def _find_revision_suggestion(proposal: dict, suggestion_id: str):
    for suggestion in proposal.get("revision_suggestions", []):
        if suggestion.get("suggestion_id") == suggestion_id:
            return suggestion
    return None


def _set_revision_suggestion_status(db: Database, proposal_id: str, suggestion_id: str, status: str):
    proposal = db.get_proposal_by_id(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    suggestions = proposal.get("revision_suggestions", [])
    updated = False
    for suggestion in suggestions:
        if suggestion.get("suggestion_id") == suggestion_id:
            suggestion["status"] = status
            suggestion[f"{status}_at"] = datetime.utcnow()
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    db.proposals_col.update_one(
        {"proposal_id": proposal_id},
        {"$set": {"revision_suggestions": suggestions, "revision_suggestions_updated_at": datetime.utcnow()}},
    )
    return next(s for s in suggestions if s.get("suggestion_id") == suggestion_id)


@router.get("")
async def list_proposals(_: str = Depends(is_admin)):
    """List all generated proposals with engagement stats (no HTML content)."""
    db = Database(APP_DB_NAME)
    proposals = db.get_all_proposals_list()
    return proposals


@router.get("/{proposal_id}/engagement")
async def proposal_engagement(proposal_id: str, _: str = Depends(is_admin)):
    """Get detailed engagement data for a specific proposal."""
    db = Database(APP_DB_NAME)
    data = db.get_proposal_engagement(proposal_id)
    if not data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return data


@router.delete("/{proposal_id}")
async def archive_proposal(proposal_id: str, _: str = Depends(is_admin)):
    """Archive (soft-delete) a proposal."""
    db = Database(APP_DB_NAME)
    db.proposals_col.update_one(
        {"proposal_id": proposal_id},
        {"$set": {"status": "archived"}}
    )
    return {"message": "Proposal archived", "proposal_id": proposal_id}


@router.get("/{proposal_id}/revision-suggestions")
async def list_revision_suggestions(proposal_id: str, _: str = Depends(is_admin)):
    """Return stored proposal revision suggestions, if any."""
    db = Database(APP_DB_NAME)
    proposal = _proposal_doc(db, proposal_id)
    return {
        "proposal_id": proposal_id,
        "revision_suggestions": proposal.get("revision_suggestions", []),
        "count": len(proposal.get("revision_suggestions", [])),
    }


@router.post("/{proposal_id}/revision-suggestions/generate")
async def generate_revision_suggestions(
    proposal_id: str,
    body: SuggestionGenerateRequest | None = None,
    _: str = Depends(is_admin),
):
    """Generate buyer-question-driven revision suggestions for a proposal."""
    db = Database(APP_DB_NAME)
    proposal = _proposal_doc(db, proposal_id)

    existing = proposal.get("revision_suggestions", [])
    if existing and body and not body.force:
        return {
            "proposal_id": proposal_id,
            "revision_suggestions": existing,
            "count": len(existing),
            "message": "Existing suggestions returned. Pass force=true to regenerate.",
        }

    suggestions = _generate_suggestions_for_proposal(proposal)
    _store_revision_suggestions(db, proposal_id, suggestions)

    return {
        "proposal_id": proposal_id,
        "revision_suggestions": suggestions,
        "count": len(suggestions),
    }


@router.post("/{proposal_id}/revision-suggestions/{suggestion_id}/apply")
async def apply_revision_suggestion(
    proposal_id: str,
    suggestion_id: str,
    current_user: dict = Depends(get_current_user),
    _: str = Depends(is_admin),
):
    """Mark a revision suggestion as applied and persist the change."""
    db = Database(APP_DB_NAME)
    proposal = _proposal_doc(db, proposal_id)
    suggestion = _find_revision_suggestion(proposal, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    updated_suggestion = _set_revision_suggestion_status(db, proposal_id, suggestion_id, "applied")
    db.proposals_col.update_one(
        {"proposal_id": proposal_id},
        {"$set": {
            "last_applied_revision": {
                "suggestion_id": suggestion_id,
                "section_name": updated_suggestion.get("section_name"),
                "suggested_copy": updated_suggestion.get("suggested_copy"),
                "applied_at": updated_suggestion.get("applied_at"),
            }
        }},
    )
    db.save_agent_action(
        agent="proposal_ops",
        action="revision_suggestion_applied",
        input_data={"proposal_id": proposal_id, "suggestion_id": suggestion_id},
        output_data={
            "section_name": updated_suggestion.get("section_name"),
            "status": updated_suggestion.get("status"),
        },
        user_id=current_user.get("email"),
        metadata={
            "proposal_id": proposal_id,
            "section_name": updated_suggestion.get("section_name"),
            "suggestion_id": suggestion_id,
        },
    )
    return {
        "message": "Suggestion applied",
        "proposal_id": proposal_id,
        "suggestion": updated_suggestion,
    }


@router.post("/{proposal_id}/revision-suggestions/{suggestion_id}/dismiss")
async def dismiss_revision_suggestion(
    proposal_id: str,
    suggestion_id: str,
    current_user: dict = Depends(get_current_user),
    _: str = Depends(is_admin),
):
    """Mark a revision suggestion as dismissed."""
    db = Database(APP_DB_NAME)
    _proposal_doc(db, proposal_id)
    updated_suggestion = _set_revision_suggestion_status(db, proposal_id, suggestion_id, "dismissed")
    db.save_agent_action(
        agent="proposal_ops",
        action="revision_suggestion_dismissed",
        input_data={"proposal_id": proposal_id, "suggestion_id": suggestion_id},
        output_data={
            "section_name": updated_suggestion.get("section_name"),
            "status": updated_suggestion.get("status"),
        },
        user_id=current_user.get("email"),
        metadata={
            "proposal_id": proposal_id,
            "section_name": updated_suggestion.get("section_name"),
            "suggestion_id": suggestion_id,
        },
    )
    return {
        "message": "Suggestion dismissed",
        "proposal_id": proposal_id,
        "suggestion": updated_suggestion,
    }


@router.post("/{proposal_id}/regenerate-section")
async def regenerate_section_from_questions(
    proposal_id: str,
    body: SectionRegenerateRequest,
    _: str = Depends(is_admin),
):
    """Heuristically regenerate a named proposal section using buyer questions."""
    db = Database(APP_DB_NAME)
    proposal = _proposal_doc(db, proposal_id)
    section_name = _normalize_section_name(body.section_name)
    questions = _question_texts(proposal)

    matching_questions = []
    for question in questions:
        lowered = question.lower()
        section_keywords = SECTION_KEYWORDS.get(section_name, [section_name])
        if section_name == "general" or any(keyword in lowered for keyword in section_keywords):
            matching_questions.append(question)

    if not matching_questions and questions:
        matching_questions = questions[:5]

    regenerated_copy = _build_section_copy(section_name, matching_questions)
    db.proposals_col.update_one(
        {"proposal_id": proposal_id},
        {
            "$set": {
                f"regenerated_sections.{section_name}": {
                    "section_name": section_name,
                    "regenerated_copy": regenerated_copy,
                    "source_questions": matching_questions[:10],
                    "updated_at": datetime.utcnow(),
                },
                "last_regenerated_section": section_name,
            }
        },
    )

    return {
        "proposal_id": proposal_id,
        "section_name": section_name,
        "regenerated_copy": regenerated_copy,
        "source_questions": matching_questions[:10],
    }


# ─── Follow-up config & auto-follow-up for stale proposals ──────────────


class FollowupConfigRequest(BaseModel):
    enabled: bool = True
    delay_hours: int = Field(default=48, ge=12, le=168)


@router.get("/followup-config")
async def get_followup_config(current_user: dict = Depends(get_current_user), _: str = Depends(is_admin)):
    """Return the current auto-follow-up configuration."""
    db = Database(APP_DB_NAME)
    return db.get_followup_config(current_user["email"])


@router.post("/followup-config")
async def save_followup_config(
    body: FollowupConfigRequest,
    current_user: dict = Depends(get_current_user),
    _: str = Depends(is_admin),
):
    """Enable/disable auto-follow-up and set the stale-hours threshold."""
    db = Database(APP_DB_NAME)
    return db.save_followup_config(current_user["email"], body.enabled, body.delay_hours)


@router.get("/stale")
async def list_stale_proposals(
    hours: int = 48,
    _: str = Depends(is_admin),
):
    """Return proposals with buyer activity older than `hours` that have not received a follow-up."""
    db = Database(APP_DB_NAME)
    stale = db.get_stale_proposals(stale_hours=hours)
    return {"stale_proposals": stale, "count": len(stale), "threshold_hours": hours}


def _build_followup_email(proposal: dict) -> dict:
    """Build a follow-up email for a stale proposal."""
    title = proposal.get("title") or "your proposal"
    sessions = proposal.get("buyer_sessions", [])
    buyer_emails = list({s.get("buyer_email") for s in sessions if s.get("buyer_email")})
    buyer_names = list({s.get("buyer_name") for s in sessions if s.get("buyer_name")})

    # Find the most-asked topic to personalise the email
    questions = _question_texts(proposal)
    top_topic = "our proposal"
    if questions:
        buckets = _detect_sections_from_questions(questions)
        largest = max(buckets.items(), key=lambda kv: len(kv[1]), default=("general", []))
        top_topic = largest[0] if largest[0] != "general" else "our proposal"

    name_str = buyer_names[0] if buyer_names else "there"
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
    proposal_id = proposal.get("proposal_id", "")
    proposal_link = f"{frontend_url}/proposal/{proposal_id}"

    subject = f"Still have questions about {title}?"
    body = (
        f"Hi {name_str},\n\n"
        f"I noticed you had a chance to review our proposal.\n"
        f"It looks like you were particularly interested in {top_topic}. "
        f"Happy to walk you through it — feel free to reply or revisit the proposal here:\n\n"
        f"{proposal_link}\n\n"
        f"Best regards,\nThe Pravaha Team"
    )

    return {
        "subject": subject,
        "body": body,
        "recipients": buyer_emails,
        "proposal_id": proposal_id,
        "top_topic": top_topic,
    }


@router.post("/trigger-followups")
async def trigger_followups(
    current_user: dict = Depends(get_current_user),
    _: str = Depends(is_admin),
):
    """
    Check for stale proposals and send auto-follow-up emails.
    Returns the list of proposals that received follow-ups.
    """
    from .sendbulk import send_mails

    db = Database(APP_DB_NAME)
    config = db.get_followup_config(current_user["email"])
    delay_hours = config.get("delay_hours", 48)
    stale = db.get_stale_proposals(stale_hours=delay_hours)

    sent = []
    for proposal in stale:
        email_data = _build_followup_email(proposal)
        recipients = email_data["recipients"]
        if not recipients:
            continue
        try:
            send_mails(
                subject=email_data["subject"],
                body=email_data["body"],
                mail_list=recipients,
                sent_by=current_user.get("email"),
            )
            db.mark_followup_sent(
                proposal["proposal_id"],
                recipients=recipients,
                subject=email_data["subject"],
                top_topic=email_data["top_topic"],
            )
            db.save_agent_action(
                agent="proposal_ops",
                action="followup_sent",
                input_data={
                    "proposal_id": proposal["proposal_id"],
                    "recipients": recipients,
                    "subject": email_data["subject"],
                },
                output_data={"top_topic": email_data["top_topic"]},
                user_id=current_user.get("email"),
                metadata={"proposal_id": proposal["proposal_id"], "recipient_count": len(recipients)},
            )
            sent.append({
                "proposal_id": proposal["proposal_id"],
                "recipients": recipients,
                "subject": email_data["subject"],
                "top_topic": email_data["top_topic"],
            })
        except Exception as exc:
            db.save_agent_action(
                agent="proposal_ops",
                action="followup_send_failed",
                input_data={"proposal_id": proposal["proposal_id"]},
                output_data={"error": str(exc)},
                status="error",
                user_id=current_user.get("email"),
                metadata={"proposal_id": proposal["proposal_id"]},
            )
            sent.append({
                "proposal_id": proposal["proposal_id"],
                "error": str(exc),
            })

    message = f"Processed {len(stale)} stale proposals."
    if not config.get("enabled"):
        message = f"Processed {len(stale)} stale proposals while auto-follow-up is disabled."

    return {
        "message": message,
        "sent": sent,
        "count": len(sent),
        "stale_count": len(stale),
        "auto_followup_enabled": bool(config.get("enabled")),
    }
