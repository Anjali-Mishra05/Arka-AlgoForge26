from datetime import datetime, timedelta
from collections import Counter
from typing import Any, Dict, List, Optional
import os
import uuid

from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()

LEGACY_DB_NAME = os.getenv("LEGACY_DB_NAME", "pravaha")
APP_DB_NAME = os.getenv("APP_DB_NAME", "pravaha_app")
DEFAULT_CRM_SYNC_PREFERENCES = {
    "proposal_generated": True,
    "buyer_engagement": True,
    "call_summary": True,
    "bulk_email": True,
}


def normalize_crm_sync_preferences(preferences: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
    normalized = dict(DEFAULT_CRM_SYNC_PREFERENCES)
    for key, value in (preferences or {}).items():
        if key in normalized:
            normalized[key] = bool(value)
    return normalized

# Singleton MongoClient — created once, reused across all requests
_mongo_client: Optional[MongoClient] = None


def _get_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(
            os.environ["CONNECTION_STRING"],
            serverSelectionTimeoutMS=5000,
        )
    return _mongo_client


class Database:
    def __init__(self, db_name: str):
        self.client = _get_client()
        self.db = self.client[db_name]

        self.chats = self.db["chats"]
        self.endpoints = self.db["endpoints"]
        self.legacy_proposals = self.db["proposal"]
        self.proposals_col = self.db["proposals"]
        self.calls_col = self.db["calls"]
        self.sync_log = self.db["sync_log"]
        self.onboarding = self.db["onboarding"]
        self.agent_actions = self.db["agent_actions"]
        self.automations = self.db["automations"]
        self.automation_runs = self.db["automation_runs"]
        self.proposal_revision_suggestions = self.db["proposal_revision_suggestions"]
        self.daily_briefs = self.db["daily_briefs"]
        self.next_best_actions = self.db["next_best_actions"]
        self.email_campaigns = self.db["email_campaigns"]
        self.followup_config = self.db["followup_config"]
        self.notifications = self.db["notifications"]

    def _now(self) -> datetime:
        return datetime.utcnow()

    def _clean_doc(self, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not doc:
            return None
        return {key: value for key, value in doc.items() if key != "_id"}

    def _parse_dt(self, value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        return None

    def _question_count(self, messages: List[Dict[str, Any]]) -> int:
        return len([message for message in messages if message.get("role") == "user"])

    def _normalize_question_text(self, content: Any) -> str:
        if not content:
            return ""
        normalized = " ".join(str(content).strip().lower().split())
        return normalized.rstrip("?.! ")

    def _latest_buyer_activity(self, sessions: List[Dict[str, Any]]) -> Optional[datetime]:
        activity_points = [
            session.get("last_active") or session.get("started_at")
            for session in sessions
            if session.get("last_active") or session.get("started_at")
        ]
        datetimes = [point for point in activity_points if isinstance(point, datetime)]
        return max(datetimes, default=None)

    def _buyer_session_summary(self, session: Dict[str, Any]) -> Dict[str, Any]:
        messages = session.get("messages", [])
        buyer_messages = [message for message in messages if message.get("role") == "user"]
        assistant_messages = [message for message in messages if message.get("role") == "assistant"]
        first_question = buyer_messages[0] if buyer_messages else None
        last_question = buyer_messages[-1] if buyer_messages else None
        last_assistant_response = assistant_messages[-1] if assistant_messages else None
        return {
            "session_id": session.get("session_id"),
            "buyer_name": session.get("buyer_name"),
            "buyer_email": session.get("buyer_email"),
            "questions_asked": self._question_count(messages),
            "started_at": session.get("started_at"),
            "last_active": session.get("last_active") or session.get("started_at"),
            "message_count": len(messages),
            "assistant_responses": len(assistant_messages),
            "first_question": first_question.get("content") if first_question else None,
            "last_question": last_question.get("content") if last_question else None,
            "last_assistant_response": last_assistant_response.get("content") if last_assistant_response else None,
            "messages": messages,
        }

    def _question_summary(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for session in sessions:
            for message in session.get("messages", []):
                if message.get("role") != "user" or not message.get("content"):
                    continue
                normalized = self._normalize_question_text(message.get("content"))
                if not normalized:
                    continue
                bucket = grouped.setdefault(
                    normalized,
                    {
                        "question": str(message.get("content")).strip(),
                        "count": 0,
                        "session_ids": set(),
                        "buyer_names": set(),
                        "buyer_emails": set(),
                        "last_asked_at": None,
                    },
                )
                bucket["count"] += 1
                if session.get("session_id"):
                    bucket["session_ids"].add(session.get("session_id"))
                if session.get("buyer_name"):
                    bucket["buyer_names"].add(session.get("buyer_name"))
                if session.get("buyer_email"):
                    bucket["buyer_emails"].add(session.get("buyer_email"))
                asked_at = message.get("timestamp")
                if isinstance(asked_at, datetime) and (
                    not isinstance(bucket["last_asked_at"], datetime) or asked_at > bucket["last_asked_at"]
                ):
                    bucket["last_asked_at"] = asked_at

        summaries = []
        for bucket in grouped.values():
            summaries.append(
                {
                    "question": bucket["question"],
                    "count": bucket["count"],
                    "session_count": len(bucket["session_ids"]),
                    "buyer_names": sorted(bucket["buyer_names"]),
                    "buyer_emails": sorted(bucket["buyer_emails"]),
                    "last_asked_at": bucket["last_asked_at"],
                }
            )
        summaries.sort(
            key=lambda item: (
                -int(item.get("count") or 0),
                -(item.get("last_asked_at").timestamp() if isinstance(item.get("last_asked_at"), datetime) else 0),
                item.get("question") or "",
            )
        )
        return summaries

    def _engagement_timeline(
        self,
        sessions: List[Dict[str, Any]],
        view_log: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []

        for view in view_log:
            viewed_at = view.get("viewed_at")
            events.append(
                {
                    "event_type": "view",
                    "occurred_at": viewed_at,
                    "viewer_session": view.get("viewer_session"),
                    "viewer_ip": view.get("viewer_ip"),
                    "referrer": view.get("referrer"),
                    "label": "Proposal viewed",
                }
            )

        for session in sessions:
            for message in session.get("messages", []):
                role = message.get("role")
                content = str(message.get("content") or "").strip()
                occurred_at = message.get("timestamp")
                if role == "user":
                    label = "Buyer asked a question"
                elif role == "assistant":
                    label = "Pravaha answered"
                else:
                    label = "Proposal activity"
                events.append(
                    {
                        "event_type": f"{role or 'unknown'}_message",
                        "occurred_at": occurred_at,
                        "session_id": session.get("session_id"),
                        "buyer_name": session.get("buyer_name"),
                        "buyer_email": session.get("buyer_email"),
                        "content": content,
                        "label": label,
                    }
                )

        events.sort(
            key=lambda item: item.get("occurred_at") if isinstance(item.get("occurred_at"), datetime) else datetime.min,
            reverse=True,
        )
        return events[:50]

    def _events_after(self, events: List[Dict[str, Any]], after: Any) -> List[Dict[str, Any]]:
        after_dt = self._parse_dt(after)
        if not after_dt:
            return []
        return [
            event
            for event in events
            if isinstance(event.get("occurred_at"), datetime) and event.get("occurred_at") > after_dt
        ]

    def _followup_outcome(self, proposal: Dict[str, Any], events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        sent_at = self._parse_dt(proposal.get("followup_sent_at"))
        if not sent_at:
            return None
        follow_on_events = self._events_after(events, sent_at)
        if not follow_on_events:
            return {
                "status": "pending",
                "sent_at": sent_at,
                "event_count": 0,
            }
        first_event = follow_on_events[-1]
        last_event = follow_on_events[0]
        return {
            "status": "buyer_reengaged",
            "sent_at": sent_at,
            "first_reengaged_at": first_event.get("occurred_at"),
            "last_reengaged_at": last_event.get("occurred_at"),
            "event_count": len(follow_on_events),
            "latest_event_type": last_event.get("event_type"),
        }

    def _revision_outcomes(self, proposal: Dict[str, Any], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        outcomes: List[Dict[str, Any]] = []
        for suggestion in proposal.get("revision_suggestions", []) or []:
            applied_at = self._parse_dt(suggestion.get("applied_at"))
            if suggestion.get("status") != "applied" or not applied_at:
                continue
            follow_on_events = self._events_after(events, applied_at)
            outcome = {
                "suggestion_id": suggestion.get("suggestion_id"),
                "section_name": suggestion.get("section_name"),
                "applied_at": applied_at,
                "status": "engagement_after_revision" if follow_on_events else "pending",
                "event_count": len(follow_on_events),
            }
            if follow_on_events:
                outcome["first_event_at"] = follow_on_events[-1].get("occurred_at")
                outcome["last_event_at"] = follow_on_events[0].get("occurred_at")
                outcome["latest_event_type"] = follow_on_events[0].get("event_type")
            outcomes.append(outcome)
        return outcomes

    def _proposal_metrics(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        sessions = proposal.get("buyer_sessions", [])
        buyer_messages = sum(len(session.get("messages", [])) for session in sessions)
        questions = sum(self._question_count(session.get("messages", [])) for session in sessions)
        return {
            "views": proposal.get("views", 0),
            "unique_buyers": len(sessions),
            "buyer_message_count": buyer_messages,
            "buyer_question_count": questions,
            "last_view_at": proposal.get("last_view_at"),
            "latest_buyer_activity": proposal.get("latest_buyer_activity") or self._latest_buyer_activity(sessions),
        }

    def _merge_proposal_projection(self, proposal: Dict[str, Any], include_html: bool = False) -> Dict[str, Any]:
        clean = self._clean_doc(proposal) or {}
        if not include_html:
            clean.pop("html_content", None)
            clean.pop("markdown_content", None)
        clean.update(self._proposal_metrics(clean))
        return clean

    def get_sessions_by_user_id(self, user_id: str, limit: int = 10):
        doc = self.chats.find_one() or {}
        sessions = doc.get("sessions", [])
        user_sessions = [session for session in sessions if session.get("session", [{}])[0].get("user") == user_id]
        return user_sessions[-limit:]

    def insert_call_chats(self, messages):
        self.chats.insert_one(messages)

    def get_all_proposals(self):
        legacy = list(self.legacy_proposals.find())
        modern = list(self.proposals_col.find())
        return legacy + modern

    def get_texts_by_user_id(self, user_id):
        doc = self.chats.find_one() or {}
        sessions = doc.get("sessions", [])
        user_sessions = [session for session in sessions if session.get("user") == user_id]
        return [session.get("message") for session in user_sessions]

    def save_proposal(self, proposal_data):
        self.legacy_proposals.delete_many({})
        self.legacy_proposals.insert_one(proposal_data)

    def append_session(self, session):
        if self.chats.count_documents({}) == 0:
            self.chats.insert_one({"sessions": []})

        doc = self.chats.find_one() or {}
        sessions = doc.get("sessions", [])
        sessions.append(session)
        self.chats.update_one({}, {"$set": {"sessions": sessions}})

    async def update_endpoint(self, endpoint):
        filter_query = {"endpoint": endpoint}
        update_operation = {"$inc": {"count": 1}}
        self.endpoints.update_one(filter_query, update_operation, upsert=True)

    # Proposals
    def save_proposal_with_id(
        self,
        html_content: str,
        markdown_content: str,
        created_by: str,
        documents_used: list,
        proposal_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        proposal_id = proposal_id or str(uuid.uuid4())
        document = {
            "proposal_id": proposal_id,
            "created_by": created_by,
            "created_at": self._now(),
            "documents_used": documents_used,
            "html_content": html_content,
            "markdown_content": markdown_content,
            "status": "active",
            "views": 0,
            "buyer_sessions": [],
        }
        if title:
            document["title"] = title
        if metadata:
            document["metadata"] = metadata
        self.proposals_col.insert_one(document)
        return proposal_id

    def get_proposal_by_id(self, proposal_id: str, include_html: bool = True):
        proposal = self.proposals_col.find_one({"proposal_id": proposal_id}, {"_id": 0})
        if not proposal:
            proposal = self.legacy_proposals.find_one({"proposal_id": proposal_id}, {"_id": 0})
        if not proposal:
            return None
        if not include_html:
            proposal.pop("html_content", None)
            proposal.pop("markdown_content", None)
        return proposal

    def get_all_proposals_list(self):
        proposals = list(
            self.proposals_col.find({}, {"_id": 0, "html_content": 0, "markdown_content": 0}).sort("created_at", -1)
        )
        return [self._merge_proposal_projection(proposal, include_html=False) for proposal in proposals]

    def update_proposal_status(self, proposal_id: str, status: str):
        self.proposals_col.update_one(
            {"proposal_id": proposal_id},
            {"$set": {"status": status, "updated_at": self._now()}},
            upsert=False,
        )

    def increment_proposal_view(
        self,
        proposal_id: str,
        viewer_session: Optional[str] = None,
        viewer_ip: Optional[str] = None,
        referrer: Optional[str] = None,
    ):
        view_event = {
            "viewed_at": self._now(),
            "viewer_session": viewer_session,
            "viewer_ip": viewer_ip,
            "referrer": referrer,
        }
        self.proposals_col.update_one(
            {"proposal_id": proposal_id},
            {"$inc": {"views": 1}, "$push": {"view_log": view_event}, "$set": {"last_view_at": self._now()}},
        )

    def add_buyer_message(
        self,
        proposal_id: str,
        session_id: str,
        buyer_name: str,
        buyer_email: str,
        role: str,
        content: str,
    ):
        message = {"role": role, "content": content, "timestamp": self._now()}
        message_time = message["timestamp"]
        existing = self.proposals_col.find_one({"proposal_id": proposal_id, "buyer_sessions.session_id": session_id})
        if existing:
            self.proposals_col.update_one(
                {"proposal_id": proposal_id, "buyer_sessions.session_id": session_id},
                {
                    "$push": {"buyer_sessions.$.messages": message},
                    "$set": {
                        "buyer_sessions.$.last_active": message_time,
                        "latest_buyer_activity": message_time,
                    },
                },
            )
            return

        self.proposals_col.update_one(
            {"proposal_id": proposal_id},
            {
                "$push": {
                    "buyer_sessions": {
                        "session_id": session_id,
                        "buyer_name": buyer_name,
                        "buyer_email": buyer_email,
                        "started_at": message_time,
                        "last_active": message_time,
                        "messages": [message],
                    }
                },
                "$set": {"latest_buyer_activity": message_time},
            },
        )

    def get_proposal_engagement(self, proposal_id: str):
        doc = self.proposals_col.find_one({"proposal_id": proposal_id}, {"_id": 0})
        if not doc:
            doc = self.legacy_proposals.find_one({"proposal_id": proposal_id}, {"_id": 0})
        if not doc:
            return None

        sessions = doc.get("buyer_sessions", [])
        view_log = doc.get("view_log", [])
        question_summary = self._question_summary(sessions)
        flattened_questions = [item["question"] for item in question_summary for _ in range(item.get("count", 0))]
        engagement_timeline = self._engagement_timeline(sessions, view_log)

        return {
            "proposal_id": proposal_id,
            "title": doc.get("title"),
            "status": doc.get("status", "active"),
            "views": doc.get("views", 0),
            "view_log": view_log,
            "last_view_at": doc.get("last_view_at"),
            "latest_buyer_activity": doc.get("latest_buyer_activity") or self._latest_buyer_activity(sessions),
            "unique_buyers": len(sessions),
            "buyer_message_count": sum(len(session.get("messages", [])) for session in sessions),
            "buyer_question_count": len(flattened_questions),
            "most_asked_questions": [item["question"] for item in question_summary[:10]],
            "question_summary": question_summary[:10],
            "engagement_timeline": engagement_timeline,
            "followup_outcome": self._followup_outcome(doc, engagement_timeline),
            "revision_outcomes": self._revision_outcomes(doc, engagement_timeline),
            "buyer_sessions": [self._buyer_session_summary(session) for session in sessions],
        }

    def get_proposal_buyer_questions(self, proposal_id: str):
        engagement = self.get_proposal_engagement(proposal_id)
        if not engagement:
            return []

        questions = []
        for session in engagement.get("buyer_sessions", []):
            for message in session.get("messages", []):
                if message.get("role") == "user":
                    questions.append(
                        {
                            "proposal_id": proposal_id,
                            "session_id": session.get("session_id"),
                            "buyer_name": session.get("buyer_name"),
                            "buyer_email": session.get("buyer_email"),
                            "content": message.get("content"),
                            "timestamp": message.get("timestamp"),
                        }
                    )
        return questions

    def get_proposal_activity(self, proposal_id: str):
        proposal = self.get_proposal_by_id(proposal_id, include_html=False)
        if not proposal:
            return None
        engagement = self.get_proposal_engagement(proposal_id) or {}
        suggestions = self.get_proposal_revision_suggestions(proposal_id=proposal_id)
        return {
            "proposal": proposal,
            "engagement": engagement,
            "suggestions": suggestions,
        }

    # Proposal revision suggestions
    def save_proposal_revision_suggestion(
        self,
        proposal_id: str,
        section: str,
        reason: str,
        suggested_text: str,
        source_questions: Optional[List[Dict[str, Any]]] = None,
        created_by: Optional[str] = None,
        status: str = "pending",
    ) -> str:
        suggestion_id = str(uuid.uuid4())
        self.proposal_revision_suggestions.insert_one(
            {
                "suggestion_id": suggestion_id,
                "proposal_id": proposal_id,
                "section": section,
                "reason": reason,
                "suggested_text": suggested_text,
                "source_questions": source_questions or [],
                "created_by": created_by,
                "status": status,
                "created_at": self._now(),
                "updated_at": self._now(),
            }
        )
        return suggestion_id

    def get_proposal_revision_suggestions(
        self,
        proposal_id: Optional[str] = None,
        status: Optional[str] = None,
        section: Optional[str] = None,
    ):
        query: Dict[str, Any] = {}
        if proposal_id:
            query["proposal_id"] = proposal_id
        if status:
            query["status"] = status
        if section:
            query["section"] = section
        return list(self.proposal_revision_suggestions.find(query, {"_id": 0}).sort("created_at", -1))

    def update_proposal_revision_suggestion(self, suggestion_id: str, update: Dict[str, Any]):
        payload = dict(update)
        payload["updated_at"] = self._now()
        self.proposal_revision_suggestions.update_one({"suggestion_id": suggestion_id}, {"$set": payload})
        return self.get_proposal_revision_suggestion_by_id(suggestion_id)

    def get_proposal_revision_suggestion_by_id(self, suggestion_id: str):
        return self.proposal_revision_suggestions.find_one({"suggestion_id": suggestion_id}, {"_id": 0})

    def apply_proposal_revision_suggestion(self, suggestion_id: str):
        self.proposal_revision_suggestions.update_one(
            {"suggestion_id": suggestion_id},
            {"$set": {"status": "applied", "updated_at": self._now(), "resolved_at": self._now()}},
        )
        return self.get_proposal_revision_suggestion_by_id(suggestion_id)

    def dismiss_proposal_revision_suggestion(self, suggestion_id: str):
        self.proposal_revision_suggestions.update_one(
            {"suggestion_id": suggestion_id},
            {"$set": {"status": "dismissed", "updated_at": self._now(), "resolved_at": self._now()}},
        )
        return self.get_proposal_revision_suggestion_by_id(suggestion_id)

    # Call summaries
    def save_call_summary(
        self,
        call_id: str,
        phone: str,
        summary: str,
        transcript: str,
        duration: int,
        key_points: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None,
        objection_summary: Optional[Dict[str, Any]] = None,
        crm_note: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        now = self._now()
        document = {
            "call_id": call_id,
            "phone_number": phone,
            "summary": summary,
            "transcript": transcript,
            "duration_seconds": duration,
            "key_points": key_points or [],
            "next_steps": next_steps or [],
            "objection_summary": objection_summary or {},
            "crm_note": crm_note,
            "metadata": metadata or {},
            "updated_at": now,
        }
        self.calls_col.update_one(
            {"call_id": call_id},
            {"$set": document, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

    def append_live_transcript_chunk(self, call_id: str, role: str, text: str) -> None:
        cleaned_text = str(text or "").strip()
        if not call_id or not cleaned_text:
            return

        now = self._now()
        chunk = {
            "role": role or "unknown",
            "text": cleaned_text,
            "timestamp": now,
        }

        existing = self.calls_col.find_one({"call_id": call_id}, {"_id": 0, "live_transcript": {"$slice": -1}})
        last_chunk = ((existing or {}).get("live_transcript") or [None])[-1]
        if (
            isinstance(last_chunk, dict)
            and last_chunk.get("role") == chunk["role"]
            and last_chunk.get("text") == chunk["text"]
        ):
            self.calls_col.update_one(
                {"call_id": call_id},
                {"$set": {"last_transcript_at": now, "updated_at": now}},
                upsert=True,
            )
            return

        self.calls_col.update_one(
            {"call_id": call_id},
            {
                "$setOnInsert": {"call_id": call_id, "created_at": now},
                "$set": {"last_transcript_at": now, "updated_at": now},
                "$push": {"live_transcript": chunk},
            },
            upsert=True,
        )

    def get_call_by_id(self, call_id: str):
        return self.calls_col.find_one({"call_id": call_id}, {"_id": 0})

    def get_recent_calls(self, limit: int = 10):
        return list(self.calls_col.find({}, {"_id": 0}).sort("created_at", -1).limit(limit))

    def get_recent_call_insights(self, limit: int = 5):
        calls = self.get_recent_calls(limit)
        insights = []
        for call in calls:
            insights.append(
                {
                    "call_id": call.get("call_id"),
                    "phone_number": call.get("phone_number"),
                    "status": call.get("status"),
                    "summary": call.get("summary"),
                    "key_points": call.get("key_points", []),
                    "next_steps": call.get("next_steps", []),
                    "objection_summary": call.get("objection_summary", {}),
                    "crm_note": call.get("crm_note"),
                    "created_at": call.get("created_at"),
                    "duration_seconds": call.get("duration_seconds", 0),
                    "follow_up_actions": call.get("follow_up_actions", []),
                    "buying_signals": call.get("buying_signals", []),
                    "open_questions": call.get("open_questions", []),
                    "risk_level": call.get("risk_level"),
                    "recommended_next_step": call.get("recommended_next_step"),
                }
            )
        return insights

    def get_call_insight_summary(self, limit: int = 10) -> Dict[str, Any]:
        calls = self.get_recent_call_insights(limit=limit)

        risk_breakdown: Counter[str] = Counter()
        objection_counter: Counter[str] = Counter()
        signal_counter: Counter[str] = Counter()
        next_step_counter: Counter[str] = Counter()
        total_duration_seconds = 0

        for call in calls:
            total_duration_seconds += int(call.get("duration_seconds", 0) or 0)
            objection_summary = call.get("objection_summary") or {}
            risk_level = (
                objection_summary.get("risk_level")
                or call.get("risk_level")
                or "unknown"
            )
            risk_breakdown[str(risk_level).lower()] += 1

            for item in objection_summary.get("objections", []) or []:
                label = item.get("label") or item.get("type")
                if label:
                    objection_counter[str(label)] += 1

            for item in objection_summary.get("buying_signals", []) or []:
                label = item.get("label") or item.get("type")
                if label:
                    signal_counter[str(label)] += 1

            for item in call.get("buying_signals", []) or []:
                if isinstance(item, dict):
                    label = item.get("label") or item.get("type")
                    if label:
                        signal_counter[str(label)] += 1
                elif item:
                    signal_counter[str(item)] += 1

            for item in call.get("next_steps", []) or []:
                if item:
                    next_step_counter[str(item)] += 1

            for item in call.get("follow_up_actions", []) or []:
                if item:
                    next_step_counter[str(item)] += 1

        return {
            "total_calls": len(calls),
            "total_duration_seconds": total_duration_seconds,
            "average_duration_seconds": round(total_duration_seconds / len(calls), 1) if calls else 0,
            "risk_breakdown": dict(risk_breakdown),
            "top_objections": [
                {"label": label, "count": count} for label, count in objection_counter.most_common(5)
            ],
            "top_buying_signals": [
                {"label": label, "count": count} for label, count in signal_counter.most_common(5)
            ],
            "top_next_steps": [
                {"label": label, "count": count} for label, count in next_step_counter.most_common(5)
            ],
            "recent_calls": calls,
        }

    # Agent actions
    def save_agent_action(
        self,
        agent: str,
        action: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        action_id = str(uuid.uuid4())
        self.agent_actions.insert_one(
            {
                "action_id": action_id,
                "agent": agent,
                "action": action,
                "input": input_data or {},
                "output": output_data or {},
                "status": status,
                "user_id": user_id,
                "metadata": metadata or {},
                "created_at": self._now(),
            }
        )
        return action_id

    def get_agent_actions(
        self,
        limit: int = 50,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
    ):
        query: Dict[str, Any] = {}
        if agent:
            query["agent"] = agent
        if action:
            query["action"] = action
        if status:
            query["status"] = status
        return list(self.agent_actions.find(query, {"_id": 0}).sort("created_at", -1).limit(limit))

    # Automations
    def save_automation_definition(
        self,
        name: str,
        trigger: str,
        enabled: bool = True,
        scope: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = self._now()
        document = {
            "name": name,
            "trigger": trigger,
            "enabled": enabled,
            "scope": scope or {},
            "config": config or {},
            "owner_id": owner_id,
            "description": description,
            "created_at": now,
            "updated_at": now,
            "last_run_at": None,
            "last_status": None,
            "last_error": None,
        }
        self.automations.update_one(
            {"name": name},
            {
                "$set": {
                    "trigger": trigger,
                    "enabled": enabled,
                    "scope": scope or {},
                    "config": config or {},
                    "owner_id": owner_id,
                    "description": description,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "name": name,
                    "created_at": now,
                    "last_run_at": None,
                    "last_status": None,
                    "last_error": None,
                },
            },
            upsert=True,
        )
        return self.get_automation_definition(name) or document

    def get_automation_definition(self, name: str):
        return self.automations.find_one({"name": name}, {"_id": 0})

    def list_automation_definitions(self, enabled_only: bool = False):
        query: Dict[str, Any] = {}
        if enabled_only:
            query["enabled"] = True
        return list(self.automations.find(query, {"_id": 0}).sort("updated_at", -1))

    def update_automation_definition(self, name: str, update: Dict[str, Any]):
        payload = dict(update)
        payload["updated_at"] = self._now()
        self.automations.update_one({"name": name}, {"$set": payload}, upsert=False)
        return self.get_automation_definition(name)

    def toggle_automation_definition(self, name: str, enabled: bool):
        return self.update_automation_definition(name, {"enabled": enabled})

    def delete_automation_definition(self, name: str):
        self.automations.delete_one({"name": name})

    def save_automation_run(
        self,
        automation_name: str,
        status: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        run_id: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> str:
        run_id = run_id or str(uuid.uuid4())
        now = self._now()
        self.automation_runs.insert_one(
            {
                "run_id": run_id,
                "automation_name": automation_name,
                "status": status,
                "input": input_data or {},
                "output": output_data or {},
                "error": error,
                "scope": scope or {},
                "started_at": started_at or now,
                "finished_at": finished_at,
                "created_at": now,
            }
        )
        self.automations.update_one(
            {"name": automation_name},
            {
                "$set": {
                    "last_run_at": now,
                    "last_status": status,
                    "last_error": error,
                    "updated_at": now,
                }
            },
            upsert=False,
        )
        return run_id

    def get_automation_runs(self, automation_name: Optional[str] = None, limit: int = 50):
        query: Dict[str, Any] = {}
        if automation_name:
            query["automation_name"] = automation_name
        return list(self.automation_runs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit))

    # Daily briefs / caches
    def save_daily_brief(
        self,
        scope_key: str,
        brief_type: str,
        content: Dict[str, Any],
        ttl_seconds: int = 86400,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        brief_id = str(uuid.uuid4())
        document = {
            "brief_id": brief_id,
            "scope_key": scope_key,
            "brief_type": brief_type,
            "content": content,
            "metadata": metadata or {},
            "created_at": self._now(),
            "expires_at": self._now() + timedelta(seconds=ttl_seconds),
        }
        self.daily_briefs.insert_one(document)
        return brief_id

    def get_daily_brief(self, scope_key: str, brief_type: str):
        now = self._now()
        brief = self.daily_briefs.find_one(
            {"scope_key": scope_key, "brief_type": brief_type},
            {"_id": 0},
            sort=[("created_at", -1)],
        )
        if not brief:
            return None
        expires_at = self._parse_dt(brief.get("expires_at"))
        if expires_at and expires_at < now:
            self.daily_briefs.delete_many({"scope_key": scope_key, "brief_type": brief_type})
            return None
        return brief

    def get_latest_daily_briefs(self, limit: int = 20):
        now = self._now()
        briefs = list(self.daily_briefs.find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
        return [brief for brief in briefs if not self._parse_dt(brief.get("expires_at")) or self._parse_dt(brief.get("expires_at")) >= now]

    # Next-best-action
    def save_next_best_action(
        self,
        rep_id: str,
        action: Dict[str, Any],
        source: Optional[str] = None,
        expires_in_seconds: int = 86400,
    ) -> str:
        action_id = str(uuid.uuid4())
        now = self._now()
        existing = self.next_best_actions.find_one({"rep_id": rep_id}, {"_id": 0}) or {}
        document = {
            "action_id": action_id,
            "rep_id": rep_id,
            "action": action,
            "source": source,
            "created_at": now,
            "updated_at": now,
            "expires_at": now + timedelta(seconds=expires_in_seconds),
            "events": existing.get("events", []),
        }
        self.next_best_actions.update_one({"rep_id": rep_id}, {"$set": document}, upsert=True)
        return action_id

    def get_next_best_action(self, rep_id: str):
        action = self.next_best_actions.find_one({"rep_id": rep_id}, {"_id": 0})
        if not action:
            return None
        expires_at = self._parse_dt(action.get("expires_at"))
        if expires_at and expires_at < self._now():
            self.next_best_actions.delete_one({"rep_id": rep_id})
            return None
        return action

    def track_next_best_action_event(
        self,
        rep_id: str,
        event: str,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        existing = self.get_next_best_action(rep_id)
        if not existing:
            return None
        event_payload = {
            "event": event,
            "notes": notes,
            "metadata": metadata or {},
            "created_at": self._now(),
        }
        self.next_best_actions.update_one(
            {"rep_id": rep_id},
            {
                "$push": {"events": event_payload},
                "$set": {"updated_at": self._now(), "last_event_at": event_payload["created_at"]},
            },
        )
        return self.get_next_best_action(rep_id)

    # Metrics helpers for manager briefs / rep dashboards
    def get_manager_daily_metrics(self, manager_id: str, lookback_days: int = 7):
        since = self._now() - timedelta(days=lookback_days)

        proposals = list(self.proposals_col.find({"created_by": manager_id, "created_at": {"$gte": since}}, {"_id": 0}))
        calls = list(self.calls_col.find({"created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", -1))
        sync_events = list(self.sync_log.find({"timestamp": {"$gte": since}}, {"_id": 0}).sort("timestamp", -1))
        suggestions = list(
            self.proposal_revision_suggestions.find({"created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", -1)
        )

        return {
            "manager_id": manager_id,
            "lookback_days": lookback_days,
            "proposal_count": len(proposals),
            "call_count": len(calls),
            "sync_event_count": len(sync_events),
            "revision_suggestion_count": len(suggestions),
            "top_proposals": [self._merge_proposal_projection(proposal, include_html=False) for proposal in proposals[:10]],
            "recent_calls": calls[:10],
            "recent_sync_events": sync_events[:10],
            "recent_suggestions": suggestions[:10],
        }

    def get_rep_activity(self, rep_id: str, lookback_days: int = 7):
        since = self._now() - timedelta(days=lookback_days)

        proposals = list(self.proposals_col.find({"created_by": rep_id, "created_at": {"$gte": since}}, {"_id": 0}))
        calls = list(self.calls_col.find({"created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", -1))
        actions = list(self.agent_actions.find({"user_id": rep_id, "created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", -1))
        automations = list(self.automation_runs.find({"scope.rep_id": rep_id, "created_at": {"$gte": since}}, {"_id": 0}).sort("created_at", -1))

        return {
            "rep_id": rep_id,
            "lookback_days": lookback_days,
            "proposal_count": len(proposals),
            "call_count": len(calls),
            "agent_action_count": len(actions),
            "automation_run_count": len(automations),
            "recent_proposals": [self._merge_proposal_projection(proposal, include_html=False) for proposal in proposals[:10]],
            "recent_calls": calls[:10],
            "recent_agent_actions": actions[:10],
            "recent_automation_runs": automations[:10],
        }

    # Email campaign tracking
    def save_email_campaign(
        self,
        subject: str,
        body: str,
        recipients: List[str],
        sent_count: int,
        failed_count: int,
        results: List[Dict[str, Any]],
        sent_by: Optional[str] = None,
    ) -> str:
        campaign_id = str(uuid.uuid4())
        self.email_campaigns.insert_one(
            {
                "campaign_id": campaign_id,
                "subject": subject,
                "body": body,
                "recipients": recipients,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "results": results,
                "sent_by": sent_by,
                "created_at": self._now(),
            }
        )
        return campaign_id

    def get_recent_email_campaigns(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(
            self.email_campaigns.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
        )

    def get_email_insights(self, limit: int = 20) -> Dict[str, Any]:
        campaigns = self.get_recent_email_campaigns(limit)
        if not campaigns:
            return {"total_campaigns": 0, "total_sent": 0, "top_subjects": [], "themes": []}

        total_sent = sum(c.get("sent_count", 0) for c in campaigns)
        subjects = [c.get("subject", "") for c in campaigns if c.get("subject")]

        # Extract common themes from subject lines
        theme_words: Dict[str, int] = {}
        theme_keywords = {
            "pricing": ["price", "pricing", "cost", "discount", "offer", "deal"],
            "follow-up": ["follow", "checking", "touch base", "update", "reminder"],
            "product": ["feature", "product", "launch", "new", "release", "update"],
            "roi": ["roi", "return", "value", "impact", "results", "case study"],
            "demo": ["demo", "trial", "walkthrough", "preview", "showcase"],
            "onboarding": ["onboarding", "getting started", "welcome", "setup"],
        }
        for subject in subjects:
            lowered = subject.lower()
            for theme, keywords in theme_keywords.items():
                if any(kw in lowered for kw in keywords):
                    theme_words[theme] = theme_words.get(theme, 0) + 1

        sorted_themes = sorted(theme_words.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_campaigns": len(campaigns),
            "total_sent": total_sent,
            "top_subjects": subjects[:10],
            "themes": [{"theme": t, "count": c} for t, c in sorted_themes],
            "recent_campaigns": [
                {
                    "campaign_id": c.get("campaign_id"),
                    "subject": c.get("subject"),
                    "sent_count": c.get("sent_count", 0),
                    "failed_count": c.get("failed_count", 0),
                    "created_at": c.get("created_at"),
                }
                for c in campaigns[:5]
            ],
        }

    # Follow-up config
    def get_followup_config(self, user_id: str) -> Dict[str, Any]:
        config = self.followup_config.find_one({"user_id": user_id}, {"_id": 0})
        return config or {
            "user_id": user_id,
            "enabled": False,
            "delay_hours": 48,
        }

    def save_followup_config(self, user_id: str, enabled: bool, delay_hours: int = 48) -> Dict[str, Any]:
        doc = {
            "user_id": user_id,
            "enabled": enabled,
            "delay_hours": delay_hours,
            "updated_at": self._now(),
        }
        self.followup_config.update_one(
            {"user_id": user_id},
            {"$set": doc, "$setOnInsert": {"created_at": self._now()}},
            upsert=True,
        )
        return self.get_followup_config(user_id)

    def get_stale_proposals(self, stale_hours: int = 48) -> List[Dict[str, Any]]:
        """Return active proposals with buyer sessions where last activity is older than stale_hours."""
        cutoff = self._now() - timedelta(hours=stale_hours)
        proposals = list(self.proposals_col.find(
            {"status": "active", "buyer_sessions": {"$exists": True, "$ne": []}},
            {"_id": 0, "html_content": 0, "markdown_content": 0},
        ))
        stale = []
        for p in proposals:
            if p.get("followup_sent"):
                continue
            sessions = p.get("buyer_sessions", [])
            if not sessions:
                continue
            latest_activity = max(
                (s.get("last_active") or s.get("started_at") or self._now() for s in sessions),
                default=self._now(),
            )
            if isinstance(latest_activity, datetime) and latest_activity < cutoff:
                p["latest_buyer_activity"] = latest_activity
                stale.append(p)
        return stale

    def mark_followup_sent(
        self,
        proposal_id: str,
        recipients: Optional[List[str]] = None,
        subject: Optional[str] = None,
        top_topic: Optional[str] = None,
    ):
        event = {
            "sent_at": self._now(),
            "recipients": recipients or [],
            "subject": subject,
            "top_topic": top_topic,
        }
        self.proposals_col.update_one(
            {"proposal_id": proposal_id},
            {
                "$set": {
                    "followup_sent": True,
                    "followup_sent_at": event["sent_at"],
                    "last_followup": event,
                },
                "$push": {"followup_history": event},
            },
        )

    def get_cross_channel_insights(self, lookback_days: int = 7):
        since = self._now() - timedelta(days=lookback_days)
        proposals = list(self.proposals_col.find({"created_at": {"$gte": since}}, {"_id": 0}))
        calls = list(self.calls_col.find({"created_at": {"$gte": since}}, {"_id": 0}))
        sync_events = list(self.sync_log.find({"timestamp": {"$gte": since}}, {"_id": 0}))
        return {
            "lookback_days": lookback_days,
            "proposal_count": len(proposals),
            "call_count": len(calls),
            "sync_event_count": len(sync_events),
            "proposal_views": sum(proposal.get("views", 0) for proposal in proposals),
            "buyer_questions": sum(
                self._question_count(session.get("messages", []))
                for proposal in proposals
                for session in proposal.get("buyer_sessions", [])
            ),
        }

    # --- CRM Token Management ---
    def save_crm_tokens(self, user_id: str, provider: str, access_token: str,
                        refresh_token: str, expires_at: Optional[datetime], portal_id: str) -> None:
        """Save CRM OAuth tokens for a user."""
        integrations = self.db["integrations"]
        integrations.update_one(
            {"user_id": user_id, "provider": provider},
            {
                "$set": {
                    "user_id": user_id,
                    "provider": provider,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_at": expires_at,
                    "portal_id": portal_id,
                    "connected_at": self._now(),
                },
                "$setOnInsert": {
                    "sync_preferences": normalize_crm_sync_preferences(),
                    "created_at": self._now(),
                },
            },
            upsert=True,
        )

    def get_crm_tokens(self, user_id: str, provider: str = "hubspot") -> Optional[Dict[str, Any]]:
        """Retrieve CRM OAuth tokens for a user."""
        integrations = self.db["integrations"]
        doc = integrations.find_one({"user_id": user_id, "provider": provider}, {"_id": 0})
        if doc:
            doc["sync_preferences"] = normalize_crm_sync_preferences(doc.get("sync_preferences"))
        return doc

    def update_crm_sync_preferences(
        self,
        user_id: str,
        provider: str = "hubspot",
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, bool]:
        normalized = normalize_crm_sync_preferences(preferences)
        integrations = self.db["integrations"]
        integrations.update_one(
            {"user_id": user_id, "provider": provider},
            {
                "$set": {
                    "user_id": user_id,
                    "provider": provider,
                    "sync_preferences": normalized,
                    "updated_at": self._now(),
                },
                "$setOnInsert": {
                    "created_at": self._now(),
                },
            },
            upsert=True,
        )
        return normalized

    def delete_crm_tokens(self, user_id: str, provider: str = "hubspot") -> None:
        """Delete CRM OAuth tokens for a user."""
        integrations = self.db["integrations"]
        integrations.delete_one({"user_id": user_id, "provider": provider})

    # --- Sync Event Logging ---
    def log_sync_event(self, event: str, provider: str, entity_id: str,
                       status: str, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        """Log a CRM sync event."""
        self.sync_log.insert_one({
            "event": event,
            "provider": provider,
            "entity_id": entity_id,
            "status": status,
            "data": data or {},
            "error": error,
            "created_at": self._now(),
        })

    def get_sync_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent sync events."""
        events = list(self.sync_log.find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
        return events

    # --- Onboarding State ---
    def get_onboarding(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get onboarding state for a user."""
        doc = self.onboarding.find_one({"user_id": user_id}, {"_id": 0})
        return doc

    def upsert_onboarding(self, user_id: str, data: Dict[str, Any]) -> None:
        """Update or insert onboarding data for a user."""
        self.onboarding.update_one(
            {"user_id": user_id},
            {"$set": {**data, "updated_at": self._now()}, "$setOnInsert": {"created_at": self._now()}},
            upsert=True,
        )

    def complete_onboarding_step(self, user_id: str, step: str) -> None:
        """Mark an onboarding step as complete."""
        now = self._now()
        update: Dict[str, Any] = {
            "$addToSet": {"completed_steps": step},
            "$set": {"current_step": step, "updated_at": now},
            "$setOnInsert": {"created_at": now},
        }
        if step == "share_proposal":
            update["$set"]["completed_at"] = now
        self.onboarding.update_one(
            {"user_id": user_id},
            update,
            upsert=True,
        )

    # --- User Management (Auth) ---
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username or email."""
        users = self.db["users"]
        doc = users.find_one({"username": username}, {"_id": 0})
        if doc is None:
            doc = users.find_one({"email": username}, {"_id": 0})
        return doc

    def create_user(self, username: str, email: str, hashed_password: str,
                    role: str = "user") -> None:
        """Create a new user."""
        users = self.db["users"]
        existing = users.find_one({"username": username})
        if existing:
            raise ValueError(f"User '{username}' already exists")
        users.insert_one({
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "role": role,
            "created_at": self._now(),
        })

    # --- Coaching Tips ---

    def save_coaching_tip(self, tip: dict) -> None:
        self.db["coaching_tips"].insert_one(tip)

    def get_coaching_tips_for_call(self, call_id: str) -> list:
        return list(self.db["coaching_tips"].find(
            {"call_id": call_id}, {"_id": 0}
        ).sort("timestamp", 1))

    def get_coaching_history(self, limit: int = 50, rep_id: str = None) -> list:
        match = {}
        if rep_id:
            match["rep_id"] = rep_id
        pipeline = [
            {"$match": match},
            {"$sort": {"timestamp": -1}},
            {"$limit": limit},
            {"$lookup": {
                "from": "calls",
                "localField": "call_id",
                "foreignField": "call_id",
                "as": "call_info",
            }},
            {"$unwind": {"path": "$call_info", "preserveNullAndEmptyArrays": True}},
            {"$project": {"_id": 0, "call_info._id": 0}},
        ]
        return list(self.db["coaching_tips"].aggregate(pipeline))

    def update_coaching_tip_feedback(self, tip_id: str, feedback: str, rep_id: str) -> bool:
        result = self.db["coaching_tips"].update_one(
            {"tip_id": tip_id},
            {"$set": {
                "feedback": feedback,
                "feedback_by": rep_id,
                "feedback_at": self._now(),
            }},
        )
        return result.modified_count > 0

    def get_coaching_stats(self, days: int = 30) -> dict:
        cutoff = self._now() - timedelta(days=days)
        tips_col = self.db["coaching_tips"]

        total = tips_col.count_documents({"timestamp": {"$gte": cutoff}})
        with_feedback = tips_col.count_documents({"timestamp": {"$gte": cutoff}, "feedback": {"$ne": None}})
        helpful = tips_col.count_documents({"timestamp": {"$gte": cutoff}, "feedback": "helpful"})

        type_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        tips_by_type = {doc["_id"]: doc["count"] for doc in tips_col.aggregate(type_pipeline)}

        objection_pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}, "type": "objection"}},
            {"$group": {"_id": "$subtype", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]
        top_objections = [
            {"subtype": doc["_id"], "count": doc["count"]}
            for doc in tips_col.aggregate(objection_pipeline)
        ]

        unique_calls = len(tips_col.distinct("call_id", {"timestamp": {"$gte": cutoff}}))

        return {
            "total_tips": total,
            "tips_by_type": tips_by_type,
            "unique_calls_coached": unique_calls,
            "avg_tips_per_call": round(total / unique_calls, 1) if unique_calls > 0 else 0,
            "feedback_count": with_feedback,
            "helpful_count": helpful,
            "adoption_rate": round(helpful / with_feedback * 100, 1) if with_feedback > 0 else 0,
            "top_objections": top_objections,
            "period_days": days,
        }

    def get_coaching_leaderboard(self, days: int = 30) -> list:
        cutoff = self._now() - timedelta(days=days)
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff}}},
            {"$group": {
                "_id": "$rep_id",
                "total_tips": {"$sum": 1},
                "helpful": {"$sum": {"$cond": [{"$eq": ["$feedback", "helpful"]}, 1, 0]}},
                "calls": {"$addToSet": "$call_id"},
            }},
            {"$project": {
                "_id": 0,
                "rep_id": "$_id",
                "total_tips": 1,
                "helpful": 1,
                "calls_coached": {"$size": "$calls"},
                "adoption_rate": {
                    "$cond": [
                        {"$gt": ["$total_tips", 0]},
                        {"$multiply": [{"$divide": ["$helpful", "$total_tips"]}, 100]},
                        0,
                    ]
                },
            }},
            {"$sort": {"helpful": -1}},
            {"$limit": 20},
        ]
        return list(self.db["coaching_tips"].aggregate(pipeline))

    # --- Coaching Playbook ---

    def get_coaching_playbook(self) -> list:
        return list(self.db["coaching_playbook"].find(
            {}, {"_id": 0}
        ).sort([("category", 1), ("priority", 1)]))

    def upsert_playbook_entry(self, entry: dict) -> str:
        entry["updated_at"] = self._now()
        self.db["coaching_playbook"].update_one(
            {"entry_id": entry["entry_id"]},
            {"$set": entry},
            upsert=True,
        )
        return entry["entry_id"]

    def delete_playbook_entry(self, entry_id: str) -> bool:
        result = self.db["coaching_playbook"].delete_one({"entry_id": entry_id})
        return result.deleted_count > 0

    # ------------------------------------------------------------------
    # Zapier — API key storage (reuses integrations collection)
    # ------------------------------------------------------------------

    def save_zapier_api_key(self, user_id: str, api_key: str) -> None:
        self.db["integrations"].update_one(
            {"user_id": user_id, "provider": "zapier"},
            {"$set": {
                "user_id": user_id,
                "provider": "zapier",
                "api_key": api_key,
                "updated_at": self._now(),
            }, "$setOnInsert": {"created_at": self._now()}},
            upsert=True,
        )

    def get_zapier_api_key(self, user_id: str) -> Optional[str]:
        doc = self.db["integrations"].find_one(
            {"user_id": user_id, "provider": "zapier"},
            {"api_key": 1},
        )
        return doc.get("api_key") if doc else None

    def delete_zapier_api_key(self, user_id: str) -> bool:
        result = self.db["integrations"].delete_one(
            {"user_id": user_id, "provider": "zapier"}
        )
        return result.deleted_count > 0

    # ------------------------------------------------------------------
    # Zapier — webhook configuration
    # ------------------------------------------------------------------

    def create_zapier_webhook(
        self,
        user_id: str,
        event_type: str,
        webhook_url: str,
        label: str,
        enabled: bool = True,
    ) -> dict:
        now = self._now()
        doc = {
            "webhook_id": str(uuid.uuid4()),
            "user_id": user_id,
            "event_type": event_type,
            "webhook_url": webhook_url,
            "label": label,
            "enabled": enabled,
            "created_at": now,
            "updated_at": now,
            "last_fired_at": None,
            "last_status": None,
            "fire_count": 0,
        }
        self.db["zapier_webhooks"].insert_one(doc)
        return self._clean_doc(doc)  # type: ignore[return-value]

    def list_zapier_webhooks(self, user_id: Optional[str] = None) -> List[dict]:
        query: Dict[str, Any] = {}
        if user_id:
            query["user_id"] = user_id
        return [
            self._clean_doc(d)
            for d in self.db["zapier_webhooks"].find(query, {"_id": 0}).sort("created_at", -1)
        ]

    def get_zapier_webhook(self, webhook_id: str) -> Optional[dict]:
        return self._clean_doc(
            self.db["zapier_webhooks"].find_one({"webhook_id": webhook_id}, {"_id": 0})
        )

    def update_zapier_webhook(self, webhook_id: str, updates: Dict[str, Any]) -> bool:
        allowed = {"webhook_url", "label", "enabled"}
        safe = {k: v for k, v in updates.items() if k in allowed}
        if not safe:
            return False
        safe["updated_at"] = self._now()
        result = self.db["zapier_webhooks"].update_one(
            {"webhook_id": webhook_id}, {"$set": safe}
        )
        return result.modified_count > 0

    def delete_zapier_webhook(self, webhook_id: str) -> bool:
        result = self.db["zapier_webhooks"].delete_one({"webhook_id": webhook_id})
        return result.deleted_count > 0

    def get_webhooks_for_event(self, event_type: str) -> List[dict]:
        return [
            self._clean_doc(d)
            for d in self.db["zapier_webhooks"].find(
                {"event_type": event_type, "enabled": True}, {"_id": 0}
            )
        ]

    def record_webhook_fire(self, webhook_id: str, status: str) -> None:
        self.db["zapier_webhooks"].update_one(
            {"webhook_id": webhook_id},
            {
                "$set": {"last_fired_at": self._now(), "last_status": status},
                "$inc": {"fire_count": 1},
            },
        )

    # ------------------------------------------------------------------
    # Zapier — automation rules
    # ------------------------------------------------------------------

    def create_automation_rule(self, rule: dict) -> dict:
        rule["created_at"] = self._now()
        rule["updated_at"] = self._now()
        self.db["automation_rules"].insert_one(rule)
        return self._clean_doc(rule)  # type: ignore[return-value]

    def list_automation_rules(self, user_id: Optional[str] = None) -> List[dict]:
        query: Dict[str, Any] = {}
        if user_id:
            query["created_by"] = user_id
        return [
            self._clean_doc(d)
            for d in self.db["automation_rules"].find(query, {"_id": 0}).sort("created_at", -1)
        ]

    def get_automation_rule(self, rule_id: str) -> Optional[dict]:
        return self._clean_doc(
            self.db["automation_rules"].find_one({"rule_id": rule_id}, {"_id": 0})
        )

    def update_automation_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        allowed = {"name", "event_type", "conditions", "actions", "enabled"}
        safe = {k: v for k, v in updates.items() if k in allowed}
        if not safe:
            return False
        safe["updated_at"] = self._now()
        result = self.db["automation_rules"].update_one(
            {"rule_id": rule_id}, {"$set": safe}
        )
        return result.modified_count > 0

    def delete_automation_rule(self, rule_id: str) -> bool:
        result = self.db["automation_rules"].delete_one({"rule_id": rule_id})
        return result.deleted_count > 0

    # ------------------------------------------------------------------
    # Engagement scores
    # ------------------------------------------------------------------

    def get_engagement_score(self, proposal_id: str) -> Optional[dict]:
        return self._clean_doc(
            self.db["engagement_scores"].find_one({"proposal_id": proposal_id}, {"_id": 0})
        )

    def upsert_engagement_score(self, proposal_id: str, data: dict) -> None:
        data["updated_at"] = self._now()
        self.db["engagement_scores"].update_one(
            {"proposal_id": proposal_id},
            {"$set": data, "$setOnInsert": {"created_at": self._now()}},
            upsert=True,
        )

    def append_engagement_event(self, proposal_id: str, event: dict) -> None:
        self.db["engagement_scores"].update_one(
            {"proposal_id": proposal_id},
            {
                "$push": {"events": event},
                "$set": {"updated_at": self._now()},
                "$setOnInsert": {"created_at": self._now()},
            },
            upsert=True,
        )


    # ── Section Dwell Tracking ──────────────────────────────────────────────

    def upsert_section_dwell(
        self,
        proposal_id: str,
        viewer_session: str,
        sections: Dict[str, int],
        page_total_seconds: int = 0,
    ) -> Dict[str, Any]:
        """Atomically increment per-section dwell seconds for a viewer session."""
        now = self._now()
        inc_fields: Dict[str, Any] = {"page_total_seconds": page_total_seconds, "beacons_received": 1}
        set_fields: Dict[str, Any] = {"last_updated": now}

        for section_id, seconds in sections.items():
            safe_key = section_id.replace(".", "_")  # mongo doesn't allow dots in keys
            inc_fields[f"sections.{safe_key}.total_seconds"] = seconds
            set_fields[f"sections.{safe_key}.last_updated"] = now

        self.db["section_dwell"].update_one(
            {"proposal_id": proposal_id, "viewer_session": viewer_session},
            {
                "$inc": inc_fields,
                "$set": set_fields,
                "$setOnInsert": {"first_seen": now},
            },
            upsert=True,
        )
        return self._clean_doc(
            self.db["section_dwell"].find_one(
                {"proposal_id": proposal_id, "viewer_session": viewer_session},
                {"_id": 0},
            )
        ) or {}

    def get_section_dwell_summary(self, proposal_id: str) -> List[Dict[str, Any]]:
        """Aggregate section dwell data across all viewer sessions for a proposal."""
        docs = list(
            self.db["section_dwell"].find(
                {"proposal_id": proposal_id}, {"_id": 0, "sections": 1, "viewer_session": 1}
            )
        )
        if not docs:
            return []

        # Aggregate: section_id -> {total_seconds, unique_viewers set}
        agg: Dict[str, Dict[str, Any]] = {}
        for doc in docs:
            viewer = doc.get("viewer_session", "")
            for section_id, data in (doc.get("sections") or {}).items():
                seconds = data.get("total_seconds", 0) if isinstance(data, dict) else 0
                if section_id not in agg:
                    agg[section_id] = {"total_seconds": 0, "viewers": set()}
                agg[section_id]["total_seconds"] += seconds
                agg[section_id]["viewers"].add(viewer)

        result = [
            {
                "section_id": section_id,
                "total_seconds": info["total_seconds"],
                "unique_viewers": len(info["viewers"]),
            }
            for section_id, info in agg.items()
        ]
        result.sort(key=lambda x: x["total_seconds"], reverse=True)
        return result

    def get_section_dwell_by_session(
        self, proposal_id: str, viewer_session: str
    ) -> Optional[Dict[str, Any]]:
        return self._clean_doc(
            self.db["section_dwell"].find_one(
                {"proposal_id": proposal_id, "viewer_session": viewer_session},
                {"_id": 0},
            )
        )

    # ── Notifications ──────────────────────────────────────────────────────

    def create_notification(
        self,
        notification_type: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        import uuid
        doc = {
            "notification_id": str(uuid.uuid4()),
            "type": notification_type,
            "title": title,
            "message": message,
            "metadata": metadata or {},
            "read": False,
            "created_at": self._now(),
        }
        self.notifications.insert_one(doc)
        return self._clean_doc(doc) or doc

    def get_notifications(self, limit: int = 30, unread_only: bool = False) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if unread_only:
            query["read"] = False
        results = list(
            self.notifications.find(query, {"_id": 0})
            .sort("created_at", -1)
            .limit(limit)
        )
        return results

    def get_unread_notification_count(self) -> int:
        return self.notifications.count_documents({"read": False})

    def mark_notification_read(self, notification_id: str) -> bool:
        result = self.notifications.update_one(
            {"notification_id": notification_id},
            {"$set": {"read": True}},
        )
        return result.modified_count > 0

    def mark_all_notifications_read(self) -> int:
        result = self.notifications.update_many(
            {"read": False},
            {"$set": {"read": True}},
        )
        return result.modified_count


# Global database instance — single shared connection across the app
db = Database(LEGACY_DB_NAME)
app_db = Database(APP_DB_NAME)

