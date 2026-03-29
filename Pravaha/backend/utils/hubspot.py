"""
HubSpot CRM sync engine for Pravaha.
Handles contact/deal creation and activity logging.
"""
import os
import re
import requests
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from utils.database import APP_DB_NAME, Database, normalize_crm_sync_preferences

HUBSPOT_API_BASE = "https://api.hubapi.com"
TOKEN_REFRESH_BUFFER = timedelta(minutes=5)


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def _resolve_hubspot_integration(user_id: Optional[str] = None) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Resolve a HubSpot integration by explicit user id first, then fall back
    to the most recently connected integration so best-effort automations can
    continue to work when a caller cannot supply a user id.
    """
    db = Database(APP_DB_NAME)
    integrations = db.db["integrations"]

    if user_id:
        tokens = integrations.find_one({"user_id": user_id, "provider": "hubspot"}, {"_id": 0})
        if tokens:
            return tokens, user_id

    cursor = integrations.find({"provider": "hubspot"}, {"_id": 0}).sort(
        [("connected_at", -1), ("created_at", -1), ("updated_at", -1)]
    )
    tokens = next(cursor, None)
    if tokens:
        return tokens, tokens.get("user_id")
    return None, user_id


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _current_sync_preferences(tokens: Optional[Dict[str, Any]]) -> Dict[str, bool]:
    return normalize_crm_sync_preferences((tokens or {}).get("sync_preferences"))


def _log_skip(
    db: Database,
    event: str,
    entity_id: str,
    reason: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {"reason": reason, **(data or {})}
    db.log_sync_event(event, "hubspot", entity_id, "skipped", payload)
    return {"status": "skipped", "reason": reason}


def _resolve_access_token(
    db: Database,
    tokens: Dict[str, Any],
    user_id: Optional[str],
) -> str:
    access_token = tokens.get("access_token", "")
    if not access_token:
        raise RuntimeError("No HubSpot access token")

    expires_at = _parse_datetime(tokens.get("expires_at"))
    refresh_token_value = tokens.get("refresh_token", "")
    if not expires_at or expires_at > datetime.utcnow() + TOKEN_REFRESH_BUFFER:
        return access_token
    if not refresh_token_value:
        return access_token

    refreshed = refresh_access_token(refresh_token_value)
    refreshed_access_token = refreshed.get("access_token", access_token)
    refreshed_refresh_token = refreshed.get("refresh_token", refresh_token_value)
    expires_in = int(refreshed.get("expires_in") or 1800)
    refreshed_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    if user_id:
        db.save_crm_tokens(
            user_id=user_id,
            provider="hubspot",
            access_token=refreshed_access_token,
            refresh_token=refreshed_refresh_token,
            expires_at=refreshed_expires_at,
            portal_id=str(tokens.get("portal_id", "")),
        )
    db.log_sync_event(
        "hubspot_token_refresh",
        "hubspot",
        user_id or str(tokens.get("portal_id", "hubspot")),
        "success",
        {"expires_at": refreshed_expires_at.isoformat()},
    )
    return refreshed_access_token


def _split_name(value: str) -> tuple[str, str]:
    cleaned = (value or "").strip()
    if "@" in cleaned:
        cleaned = cleaned.split("@", 1)[0]
    parts = [part for part in re.split(r"[\s._-]+", cleaned) if part]
    if not parts:
        return "Pravaha", ""
    first = parts[0].title()
    last = " ".join(part.title() for part in parts[1:])
    return first, last


def _synthetic_email(prefix: str, seed: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", (seed or "unknown").lower()).strip("-")
    token = token[:48] or "unknown"
    return f"{prefix}-{token}@pravaha.ai"


def _resolve_sync_context(
    user_id: Optional[str],
    preference_key: str,
    sync_event: str,
    entity_id: str,
    log_body: Optional[Dict[str, Any]] = None,
) -> tuple[Optional[Database], Optional[str], Optional[Dict[str, Any]], Dict[str, bool], Optional[Dict[str, Any]]]:
    db = Database(APP_DB_NAME)
    tokens, resolved_user_id = _resolve_hubspot_integration(user_id)
    if not tokens:
        return db, resolved_user_id or user_id, None, normalize_crm_sync_preferences(), _log_skip(
            db,
            sync_event,
            entity_id,
            "No HubSpot integration",
            log_body,
        )

    preferences = _current_sync_preferences(tokens)
    if not preferences.get(preference_key, True):
        return db, resolved_user_id or user_id, tokens, preferences, _log_skip(
            db,
            sync_event,
            entity_id,
            f"{preference_key} sync disabled",
            log_body,
        )

    return db, resolved_user_id or user_id, tokens, preferences, None


# ─── OAuth helpers ──────────────────────────────────────────────────────────

def get_oauth_url(state: str = "") -> str:
    client_id = os.getenv("HUBSPOT_CLIENT_ID", "")
    redirect_uri = os.getenv("HUBSPOT_REDIRECT_URI", "")
    scopes = "crm.objects.contacts.write crm.objects.deals.write crm.objects.contacts.read"
    url = (
        f"https://app.hubspot.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes.replace(' ', '%20')}"
    )
    if state:
        url += f"&state={state}"
    return url


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange OAuth code for access + refresh tokens."""
    resp = requests.post(
        "https://api.hubapi.com/oauth/v1/token",
        data={
            "grant_type": "authorization_code",
            "client_id": os.getenv("HUBSPOT_CLIENT_ID", ""),
            "client_secret": os.getenv("HUBSPOT_CLIENT_SECRET", ""),
            "redirect_uri": os.getenv("HUBSPOT_REDIRECT_URI", ""),
            "code": code,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    resp = requests.post(
        "https://api.hubapi.com/oauth/v1/token",
        data={
            "grant_type": "refresh_token",
            "client_id": os.getenv("HUBSPOT_CLIENT_ID", ""),
            "client_secret": os.getenv("HUBSPOT_CLIENT_SECRET", ""),
            "refresh_token": refresh_token,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_portal_info(access_token: str) -> dict:
    resp = requests.get(
        f"{HUBSPOT_API_BASE}/oauth/v1/access-tokens/{access_token}",
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ─── Contact helpers ────────────────────────────────────────────────────────

def upsert_contact(access_token: str, email: str, first_name: str = "", last_name: str = "", phone: str = "") -> dict:
    """Create or update a HubSpot contact by email. Returns the contact dict."""
    payload = {
        "properties": {
            "email": email,
            "firstname": first_name,
            "lastname": last_name,
            "phone": phone,
            "hs_lead_status": "NEW",
        }
    }
    # Try to create first
    resp = requests.post(
        f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts",
        json=payload,
        headers=_headers(access_token),
        timeout=10,
    )
    if resp.status_code == 409:
        # Contact already exists - update via PATCH by email
        existing_id = resp.json().get("message", "").split(":")[-1].strip()
        if not existing_id:
            # Fetch by email
            search = requests.post(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/search",
                json={"filterGroups": [{"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}]},
                headers=_headers(access_token),
                timeout=10,
            )
            results = search.json().get("results", [])
            if results:
                existing_id = results[0]["id"]
        if existing_id:
            patch = requests.patch(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/{existing_id}",
                json=payload,
                headers=_headers(access_token),
                timeout=10,
            )
            patch.raise_for_status()
            return patch.json()
    resp.raise_for_status()
    return resp.json()


def create_deal(access_token: str, deal_name: str, contact_id: str, stage: str = "appointmentscheduled", amount: float = 0.0) -> dict:
    """Create a deal and associate it with a contact."""
    payload = {
        "properties": {
            "dealname": deal_name,
            "dealstage": stage,
            "amount": str(amount),
            "closedate": datetime.utcnow().strftime("%Y-%m-%d"),
        }
    }
    resp = requests.post(
        f"{HUBSPOT_API_BASE}/crm/v3/objects/deals",
        json=payload,
        headers=_headers(access_token),
        timeout=10,
    )
    resp.raise_for_status()
    deal = resp.json()
    deal_id = deal["id"]

    # Associate deal → contact
    assoc = requests.put(
        f"{HUBSPOT_API_BASE}/crm/v4/objects/deals/{deal_id}/associations/default/contacts/{contact_id}",
        headers=_headers(access_token),
        timeout=10,
    )
    # Association 404 is non-fatal; log but continue
    if assoc.status_code not in (200, 201, 204):
        print(f"[HubSpot] Association warning: {assoc.status_code} {assoc.text}")
    return deal


def log_activity(access_token: str, contact_id: str, subject: str, body: str, activity_type: str = "NOTE") -> dict:
    """Log a note or activity on a HubSpot contact."""
    payload = {
        "properties": {
            "hs_timestamp": str(int(datetime.utcnow().timestamp() * 1000)),
            "hs_note_body": f"**{subject}**\n\n{body}",
        }
    }
    resp = requests.post(
        f"{HUBSPOT_API_BASE}/crm/v3/objects/notes",
        json=payload,
        headers=_headers(access_token),
        timeout=10,
    )
    resp.raise_for_status()
    note = resp.json()
    note_id = note["id"]

    # Associate note → contact
    requests.put(
        f"{HUBSPOT_API_BASE}/crm/v4/objects/notes/{note_id}/associations/default/contacts/{contact_id}",
        headers=_headers(access_token),
        timeout=10,
    )
    return note


def _log_to_resolved_integration(
    user_id: Optional[str],
    entity_id: str,
    sync_event: str,
    log_body: Dict[str, Any],
    handler,
    skip_on_missing: bool = True,
) -> Dict[str, Any]:
    db = Database(APP_DB_NAME)
    tokens, resolved_user_id = _resolve_hubspot_integration(user_id)
    if not tokens:
        if skip_on_missing:
            return {"status": "skipped", "reason": "No HubSpot integration"}
        raise RuntimeError("No HubSpot integration")

    access_token = tokens.get("access_token", "")
    if not access_token:
        if skip_on_missing:
            return {"status": "skipped", "reason": "No HubSpot access token"}
        raise RuntimeError("No HubSpot access token")

    try:
        result = handler(access_token, resolved_user_id or user_id, db)
        db.log_sync_event(sync_event, "hubspot", entity_id, "success", log_body)
        return result
    except Exception as e:
        db.log_sync_event(sync_event, "hubspot", entity_id, "error", log_body, str(e))
        return {"status": "error", "detail": str(e)}


def build_crm_note_body(
    call_summary: Dict[str, Any],
    objection_summary: Optional[Dict[str, Any]] = None,
    transcript_excerpt: str = "",
) -> str:
    """Build a clean CRM note body from call intelligence."""
    objection_summary = objection_summary or {}
    summary_text = (call_summary.get("summary") or "").strip()
    duration = call_summary.get("duration_seconds")
    phone_number = call_summary.get("phone_number") or "Unknown"
    call_id = call_summary.get("call_id") or "Unknown"
    risk_level = objection_summary.get("risk_level") or "medium"
    next_step = objection_summary.get("recommended_next_step") or "Review the call and follow up with the buyer."
    objections = objection_summary.get("objections") or []
    buying_signals = objection_summary.get("buying_signals") or []
    questions = objection_summary.get("questions") or []
    action_items = objection_summary.get("action_items") or []

    lines: List[str] = [
        "Pravaha Call Summary",
        f"Call ID: {call_id}",
        f"Phone: {phone_number}",
        f"Duration: {duration or 0} seconds",
        f"Risk level: {risk_level}",
        "",
    ]

    if summary_text:
        lines.extend(["Summary:", summary_text, ""])

    if objections:
        lines.append("Objections:")
        for item in objections:
            if isinstance(item, dict):
                label = item.get("label") or item.get("type") or "objection"
                evidence = item.get("evidence") or item.get("text") or ""
                lines.append(f"- {label}: {evidence}".rstrip())
            else:
                lines.append(f"- {item}")
        lines.append("")

    if buying_signals:
        lines.append("Buying signals:")
        for item in buying_signals:
            if isinstance(item, dict):
                label = item.get("label") or item.get("type") or "signal"
                evidence = item.get("evidence") or item.get("text") or ""
                lines.append(f"- {label}: {evidence}".rstrip())
            else:
                lines.append(f"- {item}")
        lines.append("")

    if questions:
        lines.append("Open questions:")
        for item in questions:
            lines.append(f"- {item}")
        lines.append("")

    if action_items:
        lines.append("Action items:")
        for item in action_items:
            lines.append(f"- {item}")
        lines.append("")

    if transcript_excerpt:
        lines.extend(["Transcript excerpt:", transcript_excerpt[:1200], ""])

    lines.extend(["Next step:", next_step])
    return "\n".join(line for line in lines if line is not None).strip()


def build_call_crm_payload(
    call_summary: Dict[str, Any],
    objection_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return the CRM-ready note payload for a call."""
    note_body = build_crm_note_body(call_summary, objection_summary, call_summary.get("transcript") or "")
    return {
        "subject": f"Pravaha Call - {call_summary.get('phone_number') or call_summary.get('call_id') or 'Unknown'}",
        "body": note_body,
        "call_id": call_summary.get("call_id"),
        "phone_number": call_summary.get("phone_number"),
    }


# ─── High-level sync helpers ─────────────────────────────────────────────────

def sync_buyer_to_crm(user_id: str, proposal_id: str, buyer_name: str, buyer_email: str, questions_asked: int):
    """
    Called when a buyer completes a chat session on a proposal.
    Creates/updates a HubSpot contact and logs a deal + activity.
    """
    db, resolved_user_id, tokens, _, skip_result = _resolve_sync_context(
        user_id=user_id,
        preference_key="buyer_engagement",
        sync_event="buyer_synced",
        entity_id=buyer_email,
        log_body={
            "proposal_id": proposal_id,
            "buyer_name": buyer_name,
            "buyer_email": buyer_email,
            "questions_asked": questions_asked,
        },
    )
    if skip_result:
        return skip_result

    try:
        access_token = _resolve_access_token(db, tokens or {}, resolved_user_id or user_id)
        parts = buyer_name.strip().split(" ", 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
        contact = upsert_contact(access_token, buyer_email, first, last)
        contact_id = contact["id"]

        deal = create_deal(
            access_token,
            deal_name=f"Proposal {proposal_id[:8]} - {buyer_name}",
            contact_id=contact_id,
        )

        log_activity(
            access_token,
            contact_id=contact_id,
            subject=f"Pravaha Proposal Engagement - {proposal_id[:8]}",
            body=(
                f"Buyer **{buyer_name}** ({buyer_email}) viewed proposal `{proposal_id}` "
                f"and asked **{questions_asked}** questions via the AI chat widget."
            ),
        )

        db.log_sync_event(
            "buyer_synced",
            "hubspot",
            buyer_email,
            "success",
            {
                "proposal_id": proposal_id,
                "buyer_name": buyer_name,
                "buyer_email": buyer_email,
                "questions_asked": questions_asked,
                "resolved_user_id": resolved_user_id or user_id,
            },
        )
        return {"status": "synced", "contact_id": contact_id, "deal_id": deal["id"]}

    except Exception as e:
        db.log_sync_event(
            "buyer_synced",
            "hubspot",
            buyer_email,
            "error",
            {
                "proposal_id": proposal_id,
                "buyer_name": buyer_name,
                "buyer_email": buyer_email,
                "questions_asked": questions_asked,
            },
            str(e),
        )
        return {"status": "error", "detail": str(e)}


def sync_proposal_generation_to_crm(
    user_id: str,
    proposal_id: str,
    created_by: str,
    documents_used: Optional[List[str]] = None,
):
    """
    Called when a proposal is generated.
    Creates/updates a contact for the proposal owner and logs a CRM activity
    so the connected HubSpot workspace can see the generation event.
    """
    document_list = documents_used or []
    db, resolved_user_id, tokens, _, skip_result = _resolve_sync_context(
        user_id=user_id,
        preference_key="proposal_generated",
        sync_event="proposal_generated",
        entity_id=proposal_id,
        log_body={
            "created_by": created_by,
            "documents_used": document_list,
        },
    )
    if skip_result:
        return skip_result

    try:
        access_token = _resolve_access_token(db, tokens or {}, resolved_user_id or user_id)
        first, last = _split_name(created_by)
        contact_email = created_by if "@" in (created_by or "") else _synthetic_email("proposal", proposal_id)
        contact = upsert_contact(access_token, contact_email, first, last)
        contact_id = contact["id"]
        deal = create_deal(
            access_token,
            deal_name=f"Proposal {proposal_id[:8]} - Generated",
            contact_id=contact_id,
        )
        log_activity(
            access_token,
            contact_id=contact_id,
            subject=f"Pravaha Proposal Generated - {proposal_id[:8]}",
            body=(
                f"Proposal `{proposal_id}` was generated by **{created_by}**.\n\n"
                f"Documents used: {', '.join(document_list) if document_list else 'None recorded.'}"
            ),
        )

        db.proposals_col.update_one(
            {"proposal_id": proposal_id},
            {
                "$set": {
                    "hubspot_contact_id": contact_id,
                    "hubspot_deal_id": deal["id"],
                    "hubspot_synced_at": datetime.utcnow(),
                    "hubspot_synced_by": resolved_user_id or user_id,
                    "hubspot_sync_status": "synced",
                }
            },
        )
        db.log_sync_event(
            "proposal_generated",
            "hubspot",
            proposal_id,
            "success",
            {
                "created_by": created_by,
                "documents_used": document_list,
                "contact_id": contact_id,
                "deal_id": deal["id"],
                "resolved_user_id": resolved_user_id or user_id,
            },
        )
        return {"status": "synced", "contact_id": contact_id, "deal_id": deal["id"]}
    except Exception as e:
        db.log_sync_event(
            "proposal_generated",
            "hubspot",
            proposal_id,
            "error",
            {
                "created_by": created_by,
                "documents_used": documents_used or [],
            },
            str(e),
        )
        return {"status": "error", "detail": str(e)}


def sync_bulk_email_to_crm(
    user_id: Optional[str],
    subject: str,
    body: str,
    recipients: List[str],
    results: Optional[List[Dict[str, Any]]] = None,
):
    """
    Best-effort HubSpot logging for bulk email sends.
    Logs each successful recipient as a contact note when a HubSpot
    integration is available.
    """
    db, resolved_user_id, tokens, _, skip_result = _resolve_sync_context(
        user_id=user_id,
        preference_key="bulk_email",
        sync_event="bulk_email_logged",
        entity_id=subject,
        log_body={
            "recipient_count": len(recipients),
        },
    )
    if skip_result:
        return skip_result

    successful_results = results or []
    sent_recipients = [
        entry.get("recipient")
        for entry in successful_results
        if entry.get("status") == "sent" and entry.get("recipient")
    ]
    if not sent_recipients:
        sent_recipients = [recipient for recipient in recipients if recipient]

    try:
        access_token = _resolve_access_token(db, tokens or {}, resolved_user_id or user_id)
        logged = 0
        for recipient in sent_recipients:
            first, last = _split_name(recipient)
            contact = upsert_contact(access_token, recipient, first, last)
            log_activity(
                access_token,
                contact_id=contact["id"],
                subject=f"Pravaha Bulk Email - {subject}",
                body=(
                    f"Bulk email campaign sent to **{recipient}**.\n\n"
                    f"Subject: {subject}\n\n"
                    f"{body[:1200]}"
                ),
            )
            logged += 1

        db.log_sync_event(
            "bulk_email_logged",
            "hubspot",
            subject,
            "success",
            {
                "recipients_logged": logged,
                "recipient_count": len(recipients),
                "resolved_user_id": resolved_user_id or user_id,
            },
        )
        return {"status": "synced", "logged": logged}
    except Exception as e:
        db.log_sync_event(
            "bulk_email_logged",
            "hubspot",
            subject,
            "error",
            {
                "recipient_count": len(recipients),
                "resolved_user_id": resolved_user_id or user_id,
            },
            str(e),
        )
        return {"status": "error", "detail": str(e)}


def sync_call_to_crm(user_id: Optional[str], phone: str, call_summary: str, contact_name: str = "", call_id: str = ""):
    """
    Called after a call completes.
    Creates/updates a HubSpot contact and logs the call summary as a note.
    """
    db = Database(APP_DB_NAME)
    if call_id:
        existing_call = db.calls_col.find_one({"call_id": call_id}, {"_id": 0, "hubspot_sync_status": 1})
        if existing_call and existing_call.get("hubspot_sync_status") == "synced":
            return {"status": "skipped", "reason": "Already synced", "call_id": call_id}

    db, resolved_user_id, tokens, _, skip_result = _resolve_sync_context(
        user_id=user_id,
        preference_key="call_summary",
        sync_event="call_synced",
        entity_id=phone,
        log_body={"call_id": call_id},
    )
    if skip_result:
        return skip_result

    try:
        access_token = _resolve_access_token(db, tokens or {}, resolved_user_id or user_id)
        email = f"{phone.strip('+').replace(' ', '')}@call.pravaha.ai"
        parts = contact_name.strip().split(" ", 1) if contact_name else ["Unknown", ""]
        contact = upsert_contact(access_token, email, parts[0], parts[1] if len(parts) > 1 else "", phone=phone)
        contact_id = contact["id"]

        log_activity(
            access_token,
            contact_id=contact_id,
            subject=f"Pravaha Call - {phone}",
            body=call_summary or "No summary available.",
        )

        if call_id:
            db.calls_col.update_one(
                {"call_id": call_id},
                {
                    "$set": {
                        "hubspot_contact_id": contact_id,
                        "hubspot_synced_at": datetime.utcnow(),
                        "hubspot_synced_by": resolved_user_id or user_id,
                        "hubspot_sync_status": "synced",
                    }
                },
            )

        db.log_sync_event(
            "call_synced",
            "hubspot",
            phone,
            "success",
            {
                "call_id": call_id,
                "contact_id": contact_id,
                "resolved_user_id": resolved_user_id or user_id,
            },
        )
        return {"status": "synced", "contact_id": contact_id}

    except Exception as e:
        db.log_sync_event(
            "call_synced",
            "hubspot",
            phone,
            "error",
            {
                "call_id": call_id,
                "resolved_user_id": resolved_user_id or user_id,
            },
            str(e),
        )
        return {"status": "error", "detail": str(e)}
