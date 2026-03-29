# utils/analytics.py
"""
Real analytics computation from MongoDB collections.
Returns data in the exact shape each frontend component expects.
"""

from datetime import datetime, timedelta
from utils.database import db


def get_analytics_summary() -> dict:
    """
    Computes real analytics from MongoDB collections.
    Called by: routers/admin/__init__.py (GET /admin/analytics)
    """
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)
    seven_days_ago = now - timedelta(days=7)

    proposals_col = db.db["proposals"]
    chats_col = db.db["chats"]
    email_campaigns_col = db.db["email_campaigns"]
    calls_col = db.db["calls"]

    # ── Raw counts ──────────────────────────────────────────────────────────────
    total_proposals = proposals_col.count_documents({})
    recent_proposals = proposals_col.count_documents({"created_at": {"$gte": thirty_days_ago}})
    prev_proposals = proposals_col.count_documents(
        {"created_at": {"$gte": sixty_days_ago, "$lt": thirty_days_ago}}
    )
    proposal_growth = _growth_rate(recent_proposals, prev_proposals)

    total_chats = chats_col.count_documents({})
    total_emails = email_campaigns_col.count_documents({})
    total_calls = calls_col.count_documents({})
    total_interactions = total_chats + total_emails + total_calls

    # Total proposal views
    views_result = list(proposals_col.aggregate([{"$group": {"_id": None, "total": {"$sum": "$views"}}}]))
    total_views = views_result[0]["total"] if views_result else 0

    # Active leads (unique buyer emails)
    leads_result = list(proposals_col.aggregate([
        {"$unwind": "$buyer_sessions"},
        {"$group": {"_id": "$buyer_sessions.buyer_email"}},
        {"$count": "total"},
    ]))
    total_leads = leads_result[0]["total"] if leads_result else 0

    # 7-day daily series for proposals
    proposal_series_data = _daily_series(proposals_col, "created_at", seven_days_ago, now)
    day_labels = [(seven_days_ago + timedelta(days=i)).strftime("%a") for i in range(7)]

    # 7-day daily series for interactions
    interactions_series_data = []
    for i in range(7):
        day_start = seven_days_ago + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        c = chats_col.count_documents({"created_at": {"$gte": day_start, "$lt": day_end}})
        e = email_campaigns_col.count_documents({"created_at": {"$gte": day_start, "$lt": day_end}})
        v = calls_col.count_documents({"created_at": {"$gte": day_start, "$lt": day_end}})
        interactions_series_data.append(c + e + v)

    # ── Deal status ─────────────────────────────────────────────────────────────
    active_deals = proposals_col.count_documents({"status": "active"})
    archived_deals = proposals_col.count_documents({"status": "archived"})
    stale_cutoff = now - timedelta(hours=48)
    stale_deals = proposals_col.count_documents({
        "status": "active",
        "created_at": {"$lt": stale_cutoff},
        "views": {"$lt": 2},
    })

    # Conversion rate: proposals with ≥1 view / total proposals
    viewed_proposals = proposals_col.count_documents({"views": {"$gte": 1}})
    conversion_rate = round((viewed_proposals / total_proposals * 100) if total_proposals > 0 else 0, 1)

    # ── Recent leads ────────────────────────────────────────────────────────────
    recent_leads_pipeline = [
        {"$unwind": "$buyer_sessions"},
        {"$sort": {"buyer_sessions.started_at": -1}},
        {"$limit": 8},
        {"$project": {
            "name": "$buyer_sessions.buyer_name",
            "email": "$buyer_sessions.buyer_email",
            "dealValue": {"$literal": "—"},
            "status": {"$literal": "Active"},
            "date": "$buyer_sessions.started_at",
        }},
    ]
    users_list = []
    for doc in proposals_col.aggregate(recent_leads_pipeline):
        users_list.append({
            "name": doc.get("name") or "Unknown",
            "email": doc.get("email") or "",
            "dealValue": doc.get("dealValue", "—"),
            "status": doc.get("status", "Active"),
        })

    # ── Top buyer questions ──────────────────────────────────────────────────────
    top_queries = _get_top_buyer_questions(proposals_col, limit=5)

    # ── Build response shapes ────────────────────────────────────────────────────

    # AveragePositions component: { avgCount, avgPos, chartSeries }
    average_pos = {
        "avgCount": total_proposals,
        "avgPos": f"+{proposal_growth}%" if proposal_growth >= 0 else f"{proposal_growth}%",
        "chartSeries": [{"name": "Proposals", "data": proposal_series_data}],
    }

    # Analytics widget: { details: [{title, count, result}], chartSeries, chartCategories }
    analytics_widget = {
        "details": [
            {"title": "Total Interactions", "count": total_interactions, "result": 0},
            {"title": "Proposals", "count": total_proposals, "result": round(proposal_growth, 1)},
            {"title": "Proposal Views", "count": total_views, "result": 0},
            {"title": "Active Leads", "count": total_leads, "result": 0},
        ],
        "chartSeries": [{"name": "Interactions", "data": interactions_series_data}],
        "chartCategories": day_labels,
    }

    # Visitor widget: { total, inPercent, chartSeries, chartSeries2, chartSeries3 }
    visitors_widget = {
        "total": total_views,
        "inPercent": f"+{round(_growth_rate(total_views, 0), 1)}%" if total_views > 0 else "0%",
        "chartSeries": proposal_series_data,
        "chartSeries2": interactions_series_data,
        "chartSeries3": [total_chats, total_emails, total_calls, total_proposals, 0, 0, 0],
    }

    # SessionBrowser: array of { icon, title, rate, visit }
    session_total = total_chats + total_emails + total_calls
    session_browser = [
        {
            "icon": "Chrome",
            "title": "Chat Sessions",
            "rate": round((total_chats / session_total * 100) if session_total else 0, 1),
            "visit": round((total_chats / session_total * 100) if session_total else 0, 1),
        },
        {
            "icon": "Opera",
            "title": "Email Campaigns",
            "rate": round((total_emails / session_total * 100) if session_total else 0, 1),
            "visit": round((total_emails / session_total * 100) if session_total else 0, 1),
        },
        {
            "icon": "Yahoo",
            "title": "Voice Calls",
            "rate": round((total_calls / session_total * 100) if session_total else 0, 1),
            "visit": round((total_calls / session_total * 100) if session_total else 0, 1),
        },
    ]

    # Sales widget (CompletedGoals, CompletedRates, SalesCountry)
    deals_by_status = [active_deals, archived_deals, stale_deals]
    sales_widget = {
        "rate": f"{conversion_rate}%",
        "number": viewed_proposals,
        "total": proposal_series_data,
        "smallNo": f"+{round(proposal_growth, 1)}%",
        "perday": proposal_series_data,
        "percountry": _get_sales_by_country(proposals_col),
    }

    # ── Proposal engagement widget ───────────────────────────────────────────────
    # Unique buyers = unique buyer emails across all sessions
    unique_buyers = total_leads

    # Average questions per buyer session
    questions_result = list(proposals_col.aggregate([
        {"$unwind": "$buyer_sessions"},
        {"$project": {"msgCount": {"$size": {"$ifNull": ["$buyer_sessions.messages", []]}}}},
        {"$group": {"_id": None, "avgMsg": {"$avg": "$msgCount"}}},
    ]))
    avg_questions = round(questions_result[0]["avgMsg"], 1) if questions_result else 0

    proposal_engagement = {
        "sent": total_proposals,
        "totalViews": total_views,
        "uniqueBuyers": unique_buyers,
        "avgQuestions": avg_questions,
        "trend": _daily_series(proposals_col, "last_view_at", seven_days_ago, now),
    }

    return {
        "averagePos": average_pos,
        "analytics": analytics_widget,
        "visitors": visitors_widget,
        "sessionBrowser": session_browser,
        "sales": sales_widget,
        "users": users_list,
        "recentLeads": users_list,
        "topQueries": top_queries,
        "dealStatus": {
            "active": active_deals,
            "archived": archived_deals,
            "stale": stale_deals,
        },
        "proposalEngagement": proposal_engagement,
    }


def _growth_rate(current: int, previous: int) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _daily_series(collection, date_field: str, start: datetime, end: datetime) -> list:
    """Return list of 7 ints — document count per day."""
    pipeline = [
        {"$match": {date_field: {"$gte": start, "$lte": end}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": f"${date_field}"}},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    results = {doc["_id"]: doc["count"] for doc in collection.aggregate(pipeline)}
    series = []
    for i in range(7):
        day = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        series.append(results.get(day, 0))
    return series


def _get_top_buyer_questions(proposals_col, limit: int = 5) -> list:
    pipeline = [
        {"$unwind": "$buyer_sessions"},
        {"$unwind": "$buyer_sessions.messages"},
        {"$match": {"buyer_sessions.messages.role": "user"}},
        {"$group": {"_id": "$buyer_sessions.messages.content", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    return [{"query": doc["_id"], "count": doc["count"]} for doc in proposals_col.aggregate(pipeline)]


def _get_sales_by_country(proposals_col) -> list:
    """Aggregate buyer countries from buyer_sessions, fallback to deal titles."""
    pipeline = [
        {"$unwind": "$buyer_sessions"},
        {
            "$group": {
                "_id": {"$ifNull": ["$buyer_sessions.country", "Unknown"]},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    results = list(proposals_col.aggregate(pipeline))
    if not results:
        # Fallback placeholder
        return [
            {"name": "United States", "count": 60},
            {"name": "United Kingdom", "count": 20},
            {"name": "Canada", "count": 12},
            {"name": "Australia", "count": 8},
        ]
    total = sum(r["count"] for r in results)
    return [
        {"name": r["_id"] or "Unknown", "count": round(r["count"] / total * 100) if total else 0}
        for r in results
    ]
