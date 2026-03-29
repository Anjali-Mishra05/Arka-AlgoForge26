# routers/admin.py
import base64
import inspect
import os
import re
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, Field
from utils.auth import is_admin, get_current_user
from utils.database import APP_DB_NAME, Database
from typing import List

from .analytics import get_analytics
from .upload import (
    upload_to_db,
    copy_files_if_exist,
    get_list_of_selected_docs,
    get_list_of_all_docs,
)
from .ingest import ingest
from .sendbulk import send_mails
from .call import call, get_latest_summary, get_status
from .generate_proposal import generate_proposal as generate_proposal_from_docs
from .proposals import router as proposals_router
from .crm import router as crm_router
from .intelligence import router as intelligence_router
from .automations import router as automations_router
from .coaching import router as coaching_router
from .zapier import router as zapier_router

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_current_user)],
)


def _regex_query(term: str):
    return {"$regex": re.escape(term.strip()), "$options": "i"}


def _search_collection(app_db: Database, collection_name: str, search_term: str, text_fields: list[str], limit: int = 5):
    collection = app_db.db[collection_name]
    projection = {"score": {"$meta": "textScore"}}
    results: list[dict] = []

    try:
        collection.create_index([(field, "text") for field in text_fields], background=True)
        results = list(
            collection.find(
                {"$text": {"$search": search_term}},
                projection,
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        )
    except Exception:
        results = []

    if results or not search_term.strip():
        return results

    regex = _regex_query(search_term)
    fallback_query = {"$or": [{field: regex} for field in text_fields]}
    return list(collection.find(fallback_query).sort("created_at", -1).limit(limit))


@router.get("/")
async def check():
    return {"message": "Admin Endpoint"}


@router.get("/analytics")
async def analytics(_: str = Depends(is_admin)):
    return get_analytics()


@router.post("/upload_pdf")
async def upload_pdf(pdf_file: UploadFile, _: str = Depends(is_admin)):
    return upload_to_db(pdf_file)


@router.post("/update_selected_docs")
async def selected_document_list(filenames: List[str], _: str = Depends(is_admin)):
    copy_files_if_exist(filenames)


# ingest the pdfs
@router.get("/ingest")
async def ingest_pdfs(_: str = Depends(is_admin)):
    await ingest("current_user")
    return {"message": "Ingested", "status": "Done"}


@router.get("/generate_proposal")
async def generate_proposal(current_user: dict = Depends(get_current_user), _: str = Depends(is_admin)):
    return generate_proposal_from_docs(created_by=current_user.get("email", "admin"))



@router.get("/get_selected_docs")
async def get_selected_docs(_: str = Depends(is_admin)):
    return get_list_of_selected_docs()


@router.get("/get_all_docs")
async def get_all_docs(_: str = Depends(is_admin)):
    return get_list_of_all_docs()


class BulkEmailRequest(BaseModel):
    recipients: List[EmailStr] = Field(min_length=1, max_length=500)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)


@router.post("/send_bulk_email")
async def send_bulk_email(body: BulkEmailRequest, current_user: dict = Depends(get_current_user), _: str = Depends(is_admin)):
    recipients = [email.strip() for email in body.recipients]
    return send_mails(body.subject, body.body, recipients, sent_by=current_user.get("email"))


class CallRequest(BaseModel):
    phone_number: str
    script: str
    context: str = ""


@router.post("/call")
async def call_user(request: CallRequest, _: str = Depends(is_admin)):
    return call(request.phone_number, "User", request.script, request.context)


@router.get("/call_status")
async def call_status(call_id: str, _: str = Depends(is_admin)):
    return get_status(call_id)


@router.get("/get_last_summary")
async def get_last_summary(call_id: str | None = None, _: str = Depends(is_admin)):
    return get_latest_summary(call_id)


@router.get("/call_insights")
async def call_insights(limit: int = 10, _: str = Depends(is_admin)):
    db = Database(APP_DB_NAME)
    return db.get_call_insight_summary(limit=limit)


@router.get("/get_html_from_file", response_class=HTMLResponse)
async def get_html_from_file(file_name: str, _: str = Depends(is_admin)):
    file_path = "all_documents/" + file_name
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "rb") as file:
        html_content = file.read()

    return html_content


# ─── Proposal engagement routes ────────────────────────────────────────────
router.include_router(proposals_router)

# ─── CRM (HubSpot) integration routes ──────────────────────────────────────
router.include_router(crm_router)
router.include_router(automations_router)


# ─── Onboarding tracking ─────────────────────────────────────────────────────
from pydantic import BaseModel as _BM

class OnboardingStepRequest(_BM):
    step: str
    data: dict = {}


@router.post("/onboarding/step")
async def save_onboarding_step(body: OnboardingStepRequest, current_user: dict = Depends(get_current_user), _: str = Depends(is_admin)):
    db = Database(APP_DB_NAME)
    db.complete_onboarding_step(current_user["email"], body.step)
    if body.data:
        db.upsert_onboarding(current_user["email"], body.data)
    return {"status": "ok"}


@router.get("/onboarding")
async def get_onboarding_status(current_user: dict = Depends(get_current_user), _: str = Depends(is_admin)):
    db = Database(APP_DB_NAME)
    state = db.get_onboarding(current_user["email"])
    return state or {"completed_steps": [], "current_step": None}


router.include_router(intelligence_router)
router.include_router(coaching_router)

# ─── Zapier + MCP event layer ───────────────────────────────────────────────
router.include_router(zapier_router)


@router.get("/search")
async def search(
    q: str,
    types: str = "docs,proposals,calls,leads",
    current_user: dict = Depends(get_current_user),
    _: str = Depends(is_admin),
):
    """Semantic search across documents, proposals, calls, and buyer leads."""
    app_db = Database(APP_DB_NAME)
    results = []
    type_list = [t.strip().lower() for t in types.split(",") if t.strip()]
    query_lower = q.strip().lower()

    # Search documents via Pinecone
    if "docs" in type_list:
        try:
            from utils.vectorbase import query_index
            docs = query_index(q)
            if inspect.isawaitable(docs):
                docs = await docs
            if docs:
                results.append(
                    {
                        "type": "document",
                        "id": "semantic-search",
                        "title": "Knowledge Base Match",
                        "snippet": str(docs)[:200],
                        "score": 80.0,
                        "created_at": "",
                    }
                )
        except Exception:
            pass

    # Search proposals via MongoDB text search
    if "proposals" in type_list:
        try:
            proposal_results = _search_collection(
                app_db,
                "proposals",
                q,
                ["title", "html_content", "markdown_content", "buyer_sessions.messages.content"],
                limit=5,
            )
            for p in proposal_results:
                results.append({
                    "type": "proposal",
                    "id": str(p.get("proposal_id", p.get("_id", ""))),
                    "title": p.get("title", "Untitled Proposal"),
                    "snippet": p.get("html_content", "")[:200],
                    "score": float(p.get("score", 75)),
                    "created_at": str(p.get("created_at", "")),
                })
        except Exception:
            pass

    # Search call summaries
    if "calls" in type_list:
        try:
            call_results = _search_collection(
                app_db,
                "calls",
                q,
                ["summary", "transcript", "crm_note"],
                limit=5,
            )
            for c in call_results:
                results.append({
                    "type": "call",
                    "id": str(c.get("call_id", c.get("_id", ""))),
                    "title": f"Call {c.get('call_id', 'Unknown')}",
                    "snippet": c.get("summary", c.get("transcript", ""))[:200],
                    "score": float(c.get("score", 70)),
                    "created_at": str(c.get("created_at", "")),
                })
        except Exception:
            pass

    if "leads" in type_list and query_lower:
        try:
            proposals = app_db.db["proposals"].find(
                {"buyer_sessions": {"$exists": True, "$ne": []}},
                {"proposal_id": 1, "title": 1, "buyer_sessions": 1, "created_at": 1},
            )
            for proposal in proposals:
                proposal_title = proposal.get("title") or proposal.get("proposal_id") or "Untitled Proposal"
                for session in proposal.get("buyer_sessions", []) or []:
                    buyer_name = session.get("buyer_name") or "Unknown buyer"
                    buyer_email = session.get("buyer_email") or ""
                    messages = session.get("messages", []) or []
                    last_question = next(
                        (message.get("content", "") for message in reversed(messages) if message.get("role") == "user"),
                        "",
                    )
                    haystack = " ".join(
                        [
                            buyer_name,
                            buyer_email,
                            proposal_title,
                            last_question,
                            " ".join(message.get("content", "") for message in messages[-3:]),
                        ]
                    ).lower()
                    if query_lower not in haystack:
                        continue
                    question_count = sum(1 for message in messages if message.get("role") == "user")
                    results.append(
                        {
                            "type": "lead",
                            "id": f"{proposal.get('proposal_id', '')}:{session.get('session_id', '')}",
                            "title": f"{buyer_name} - {proposal_title}",
                            "snippet": buyer_email or last_question[:200] or "Buyer engagement found in proposal chat.",
                            "score": 100 + question_count,
                            "created_at": str(session.get("last_active") or session.get("started_at") or proposal.get("created_at", "")),
                        }
                    )
        except Exception:
            pass

    results.sort(key=lambda r: r["score"], reverse=True)
    return {"results": results[:10]}
