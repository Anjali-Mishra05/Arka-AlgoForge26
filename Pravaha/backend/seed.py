"""
seed.py — Populate Pravaha with realistic demo data.

Run:  python seed.py          (from Pravaha/backend/)
Reset: python seed.py --reset  (drops seeded data first)

Populates: users, proposals, calls, coaching_tips, coaching_playbook,
email_campaigns, chats, onboarding, automations, automation_runs,
daily_briefs, next_best_actions, sync_log, agent_actions, buyer sessions.
"""

import os, sys, uuid, random, argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from passlib.context import CryptContext
from pymongo import MongoClient

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Config ────────────────────────────────────────────────────────────────────
CONN = os.getenv("CONNECTION_STRING", "mongodb://localhost:27017")
AUTH_DB = os.getenv("DB_NAME", "pravaha")
APP_DB = os.getenv("APP_DB_NAME", "pravaha_app")

client = MongoClient(CONN)
auth_db = client[AUTH_DB]
app_db = client[APP_DB]

NOW = datetime.utcnow()

def ago(**kw):
    return NOW - timedelta(**kw)

def uid():
    return str(uuid.uuid4())

# ── Helpers ───────────────────────────────────────────────────────────────────

REP_NAMES = [
    ("sarah_jones", "sarah.jones@pravaha.ai", "Sarah Jones"),
    ("mike_chen", "mike.chen@pravaha.ai", "Mike Chen"),
    ("priya_patel", "priya.patel@pravaha.ai", "Priya Patel"),
    ("james_wilson", "james.wilson@pravaha.ai", "James Wilson"),
    ("lisa_garcia", "lisa.garcia@pravaha.ai", "Lisa Garcia"),
]

BUYER_NAMES = [
    ("David Kim", "david.kim@techflow.io"),
    ("Rachel Adams", "rachel.adams@meridian.co"),
    ("Tom Nguyen", "tom.nguyen@sparkretail.com"),
    ("Emily Watson", "emily.watson@northbridge.fi"),
    ("Carlos Rivera", "carlos.rivera@acmesoft.io"),
    ("Anna Schmidt", "anna.schmidt@berlintech.de"),
    ("Raj Mehta", "raj.mehta@cloudnine.in"),
    ("Sophie Laurent", "sophie.laurent@parisbiz.fr"),
    ("Ben Okafor", "ben.okafor@lagosdata.ng"),
    ("Mia Tanaka", "mia.tanaka@tokyoventures.jp"),
]

COUNTRIES = ["United States", "United Kingdom", "Canada", "India", "Germany",
             "Australia", "France", "Japan", "Brazil", "Nigeria"]

OBJECTION_TYPES = [
    ("pricing", "Too Expensive"),
    ("competitor", "Using Competitor"),
    ("timing", "Not the Right Time"),
    ("authority", "Need Approval"),
    ("roi", "No ROI Proof"),
    ("security", "Security Concerns"),
    ("complexity", "Too Complex"),
    ("budget_cycle", "Budget Cycle Mismatch"),
]

BUYING_SIGNALS = [
    ("urgency", "Asked about implementation timeline"),
    ("budget_confirmed", "Confirmed budget availability"),
    ("champion", "Offered to present internally"),
    ("technical_fit", "Asked detailed integration questions"),
    ("expansion", "Mentioned rolling out to other teams"),
    ("pricing_request", "Requested formal pricing proposal"),
]

COACHING_TIP_CONTENT = [
    ("objection", "pricing", "Try the ROI frame: at $299/mo generating $2-8K additional revenue, Pravaha pays for itself with one extra deal per month.",
     "Prospect said: 'That's way over our budget for this quarter.'"),
    ("objection", "competitor", "Differentiate on real-time coaching: Unlike Gong/Chorus which analyze AFTER the call, Pravaha coaches during the live call.",
     "Prospect said: 'We already use Gong for call analytics.'"),
    ("buying_signal", "urgency", "Buying signal detected — prospect is asking about timeline. Reinforce quick onboarding: 2-hour setup, dedicated CSM for 30 days.",
     "Prospect said: 'How quickly can we get this rolled out to the team?'"),
    ("buying_signal", "champion", "Champion identified — offer enablement materials: 1-page ROI summary for CFO, security overview for IT, demo recording for the team.",
     "Prospect said: 'I'd like to show this to my VP next week.'"),
    ("technique", "discovery", "Ask discovery questions before pitching features. Understand their current workflow pain points first.",
     "Rep jumped straight to feature demo without understanding prospect needs."),
    ("objection", "authority", "Multi-stakeholder deal detected. Offer champion enablement kit: ROI deck, security whitepaper, recorded demo.",
     "Prospect said: 'I need to run this by the board first.'"),
    ("objection", "timing", "Create urgency around cost of delay: Every month without AI coaching = X deals lost to unhandled objections.",
     "Prospect said: 'We're focused on other priorities right now.'"),
    ("buying_signal", "budget_confirmed", "Budget signal detected. Move to close: suggest a pilot start date and send contract.",
     "Prospect said: 'We have budget allocated for Q2 sales tools.'"),
    ("technique", "closing", "Use assumptive close: 'Should we schedule the onboarding for Monday or Wednesday?'",
     "Call was going well but rep didn't attempt to close."),
    ("objection", "roi", "Offer risk-free pilot: 14-day free trial, no credit card. Set up A/B test with half the team to measure conversion lift.",
     "Prospect said: 'We need to see hard numbers before committing.'"),
]

PROPOSAL_TITLES = [
    "AI Sales Platform for TechFlow SaaS",
    "Pravaha AI — Meridian Consulting Proposal",
    "Sales Automation Suite for Spark Retail",
    "Enterprise Sales Intelligence — NorthBridge Financial",
    "Pravaha Growth Plan — AcmeSoft",
    "AI-Powered Sales Coaching — BerlinTech GmbH",
    "CloudNine Sales Enablement Proposal",
    "Pravaha AI for ParisBiz International",
]

PROPOSAL_HTML = """<div style="font-family:system-ui;max-width:800px;margin:0 auto;padding:40px;">
<h1 style="color:#4F46E5;">{title}</h1>
<p>Prepared for <strong>{buyer_name}</strong> at <strong>{company}</strong></p>
<h2>Executive Summary</h2>
<p>Pravaha AI is an AI-powered sales automation platform that helps your team close more deals through real-time call coaching, intelligent proposal generation, and CRM integration.</p>
<h2>Proposed Solution</h2>
<ul>
<li><strong>AI Call Coaching</strong> — Real-time objection detection and counter-scripts during live calls</li>
<li><strong>Proposal Generation</strong> — One-click personalized proposals from your product docs</li>
<li><strong>CRM Integration</strong> — Automatic HubSpot sync of call notes, deal stages, and contacts</li>
<li><strong>Mass Email Campaigns</strong> — AI-personalized sequences with engagement tracking</li>
</ul>
<h2>Pricing</h2>
<table style="border-collapse:collapse;width:100%;">
<tr style="background:#4F46E5;color:white;"><th style="padding:10px;">Plan</th><th>Price</th><th>Users</th></tr>
<tr><td style="padding:8px;border:1px solid #ddd;">Starter</td><td style="border:1px solid #ddd;">$99/mo</td><td style="border:1px solid #ddd;">1-3</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;">Growth</td><td style="border:1px solid #ddd;">$299/mo</td><td style="border:1px solid #ddd;">Up to 10</td></tr>
<tr><td style="padding:8px;border:1px solid #ddd;">Enterprise</td><td style="border:1px solid #ddd;">Custom</td><td style="border:1px solid #ddd;">Unlimited</td></tr>
</table>
<h2>Expected ROI</h2>
<p>Based on your team of {team_size} reps, we project:</p>
<ul>
<li>+22% improvement in sales conversion rate</li>
<li>+18% increase in average deal size</li>
<li>40% faster ramp time for new reps</li>
<li>Proposal turnaround from 3 days to 15 minutes</li>
</ul>
<h2>Next Steps</h2>
<ol>
<li>Schedule a live demo with your team</li>
<li>Start 14-day free trial (no credit card required)</li>
<li>Onboarding call with dedicated Customer Success Manager</li>
</ol>
<p style="margin-top:30px;color:#6B7280;font-size:0.9em;">Generated by Pravaha AI — pravaha.ai</p>
</div>"""

BUYER_QUESTIONS = [
    "What's the onboarding process like?",
    "How does the CRM integration work with HubSpot?",
    "Can we customize the call coaching scripts?",
    "What's the pricing for a team of 15?",
    "Do you offer a free trial?",
    "How does data security work? Are you SOC 2 compliant?",
    "Can I see a live demo of the call coaching feature?",
    "What ROI have similar companies seen?",
    "How does the AI handle non-English calls?",
    "What happens if our CRM isn't HubSpot?",
    "Can we export call transcripts?",
    "How long does implementation typically take?",
    "Is there an API we can use for custom integrations?",
    "What's the contract length? Can we go month-to-month?",
    "How does the proposal generation AI work exactly?",
]

EMAIL_SUBJECTS = [
    "Pravaha AI — Transform Your Sales Team's Performance",
    "Quick follow-up: AI-powered sales coaching demo",
    "Your team is losing deals to unhandled objections",
    "Case study: How TechFlow improved conversion by 31%",
    "Pravaha AI — 14-day free trial invitation",
    "Re: Sales automation platform for {company}",
    "Your personalized ROI calculation is ready",
    "Limited time: 20% off annual plans",
    "Pravaha follow-up — any questions?",
    "3 ways AI coaching closes more deals",
]

CALL_SUMMARIES = [
    "Discussed pricing concerns. Prospect is currently using Gong but open to switching if we can demonstrate real-time coaching value. Agreed to a live demo next Tuesday. Key decision maker is VP Sales. Budget approved for Q2 tools.",
    "Cold outreach call. Prospect was initially hesitant but warmed up after hearing about the 40% conversion improvement. Asked about security compliance. Scheduled a follow-up with their IT team for security review.",
    "Demo call with 3 team members. Strong interest in proposal generation feature. Main concern is integration with their custom CRM (not HubSpot). Offered API access on Enterprise plan. Champion identified: Sales Director.",
    "Follow-up call after proposal was sent. Prospect reviewed the proposal and had questions about pricing tiers. Recommended Growth plan for their team of 8. They need board approval — sending ROI deck for internal presentation.",
    "Renewal discussion. Customer has been using Pravaha for 6 months. Conversion rate up 28%. Wants to upgrade from Growth to Scale plan and add 15 more seats. Discussing enterprise features and custom training.",
    "Discovery call with marketing agency. They handle sales for 12 clients and want a white-label solution. Discussed partnership program. Very interested in mass email + call coaching combo. Scheduling technical deep-dive.",
    "Objection-heavy call — prospect pushed back on price, timing, and ROI. Used the 'feel, felt, found' framework to handle pricing objection. Offered pilot program. Prospect agreed to 14-day trial starting next Monday.",
    "Warm referral from existing customer. Prospect already familiar with the product. Quick 15-minute call to confirm requirements. Enterprise plan with SSO and data residency in EU. Contract discussion next week.",
]

CALL_TRANSCRIPTS = [
    "Rep: Hi, this is Sarah from Pravaha AI. I'm reaching out because we help sales teams like yours close more deals with AI-powered coaching.\nProspect: Interesting, tell me more.\nRep: We provide real-time coaching during your live sales calls. Our AI listens to the conversation and suggests counter-scripts for objections, identifies buying signals, and helps your reps perform like your top performer on every single call.\nProspect: That sounds useful. We currently use Gong but it only analyzes calls after the fact.\nRep: Exactly — that's the key difference. We coach IN the moment, not after. Would you be open to a quick demo?\nProspect: Sure, let's schedule something for next week.",
    "Rep: Good afternoon, this is Mike from Pravaha AI. We spoke briefly at the conference last month.\nProspect: Right, I remember. The AI sales coaching tool.\nRep: Exactly. I wanted to follow up because you mentioned your new reps take about 5 months to ramp up.\nProspect: Yes, that's still a problem for us.\nRep: Our customers typically see ramp time cut in half — from 5 months to about 2.5 months. The AI essentially gives every new rep a personal sales coach on every call.\nProspect: What would that cost for a team of 8?\nRep: Our Growth plan at $299/month covers up to 10 users with 300 AI-coached calls per month.\nProspect: I need to check with our CFO. Can you send me an ROI breakdown?",
]


# ── Seed Functions ────────────────────────────────────────────────────────────

def seed_users():
    """Create admin + team + regular users."""
    users = auth_db["users"]
    created = 0
    # Admin
    if not users.find_one({"username": "admin"}):
        users.insert_one({
            "username": "admin",
            "email": "admin@pravaha.ai",
            "hashed_password": pwd_context.hash("admin"),
            "role": "admin",
            "created_at": ago(days=90),
        })
        created += 1

    # Team (sales reps)
    for username, email, _ in REP_NAMES:
        if not users.find_one({"username": username}):
            users.insert_one({
                "username": username,
                "email": email,
                "hashed_password": pwd_context.hash("team123"),
                "role": "team",
                "created_at": ago(days=random.randint(30, 80)),
            })
            created += 1

    # Regular user
    if not users.find_one({"username": "demo_user"}):
        users.insert_one({
            "username": "demo_user",
            "email": "demo@example.com",
            "hashed_password": pwd_context.hash("demo123"),
            "role": "user",
            "created_at": ago(days=60),
        })
        created += 1

    print(f"  Users: {created} created")


def seed_onboarding():
    """Mark admin onboarding as complete."""
    app_db["onboarding"].update_one(
        {"user_id": "admin@pravaha.ai"},
        {"$set": {
            "user_id": "admin@pravaha.ai",
            "completed_steps": [
                "company_profile", "upload_docs", "ingest",
                "test_chat", "generate_proposal", "invite_team"
            ],
            "current_step": "done",
            "completed_at": ago(days=85),
            "created_at": ago(days=90),
            "updated_at": ago(days=85),
            "company_name": "Pravaha AI",
            "company_description": "AI-powered sales automation platform that helps teams close more deals with real-time coaching, proposal generation, and CRM integration.",
            "industry": "SaaS / Sales Technology",
            "website": "https://pravaha.ai",
            "target_personas": ["VP Sales", "Sales Director", "Head of Revenue", "CRO", "Sales Ops Manager"],
        }},
        upsert=True,
    )
    print("  Onboarding: complete")


def seed_proposals():
    """Create proposals with buyer sessions and view history."""
    col = app_db["proposals"]
    created = 0

    for i, title in enumerate(PROPOSAL_TITLES):
        proposal_id = uid()
        buyer = BUYER_NAMES[i % len(BUYER_NAMES)]
        company = buyer[1].split("@")[1].split(".")[0].title()
        team_size = random.choice([5, 8, 12, 15, 20, 28, 50])
        days_old = random.randint(2, 45)
        created_at = ago(days=days_old)
        views = random.randint(1, 18)
        status = random.choice(["active", "active", "active", "archived"])

        # Generate view log
        view_log = []
        for v in range(views):
            view_log.append({
                "viewed_at": created_at + timedelta(hours=random.randint(1, days_old * 24)),
                "viewer_session": uid()[:8],
                "viewer_ip": f"192.168.{random.randint(1,10)}.{random.randint(1,254)}",
                "referrer": random.choice(["email", "direct", "slack", "email", "email"]),
            })

        # Generate buyer sessions with chat messages
        buyer_sessions = []
        num_sessions = random.randint(1, 3)
        for s in range(num_sessions):
            b = BUYER_NAMES[(i + s) % len(BUYER_NAMES)]
            messages = []
            num_msgs = random.randint(2, 6)
            session_start = created_at + timedelta(hours=random.randint(2, days_old * 12))
            for m in range(num_msgs):
                is_user = m % 2 == 0
                messages.append({
                    "role": "user" if is_user else "assistant",
                    "content": random.choice(BUYER_QUESTIONS) if is_user else f"Great question! {random.choice(['Our onboarding takes just 2 hours.', 'Yes, we offer a 14-day free trial.', 'We are SOC 2 Type II certified.', 'The Growth plan at $299/mo covers up to 10 users.', 'Our HubSpot integration syncs automatically after every call.'])}",
                    "timestamp": session_start + timedelta(minutes=m * random.randint(1, 5)),
                })
            buyer_sessions.append({
                "session_id": uid(),
                "buyer_name": b[0],
                "buyer_email": b[1],
                "country": random.choice(COUNTRIES),
                "started_at": session_start,
                "last_active": messages[-1]["timestamp"],
                "messages": messages,
            })

        html = PROPOSAL_HTML.format(
            title=title, buyer_name=buyer[0],
            company=company, team_size=team_size,
        )

        col.insert_one({
            "proposal_id": proposal_id,
            "created_by": "admin@pravaha.ai",
            "created_at": created_at,
            "updated_at": created_at + timedelta(hours=random.randint(1, 48)),
            "title": title,
            "html_content": html,
            "markdown_content": f"# {title}\n\nProposal for {buyer[0]} at {company}.",
            "documents_used": ["pravaha_test_sales_doc.pdf", "proposal.md"],
            "metadata": {"team_size": team_size, "plan": random.choice(["Starter", "Growth", "Scale", "Enterprise"])},
            "status": status,
            "views": views,
            "view_log": view_log,
            "buyer_sessions": buyer_sessions,
            "last_view_at": view_log[-1]["viewed_at"] if view_log else created_at,
            "latest_buyer_activity": buyer_sessions[-1]["last_active"] if buyer_sessions else None,
            "revision_suggestions": [],
            "proposal": html,  # legacy field used by chatbot
        })
        created += 1

    print(f"  Proposals: {created} created")


def seed_calls():
    """Create call records with rich intelligence data."""
    col = app_db["calls"]
    created = 0

    for i in range(12):
        rep = REP_NAMES[i % len(REP_NAMES)]
        buyer = BUYER_NAMES[i % len(BUYER_NAMES)]
        days_old = random.randint(1, 30)
        duration = random.randint(120, 900)
        risk = random.choice(["low", "low", "medium", "medium", "high"])

        # Pick 1-3 objections
        call_objections = random.sample(OBJECTION_TYPES, k=random.randint(1, 3))
        # Pick 1-3 buying signals
        call_signals = random.sample(BUYING_SIGNALS, k=random.randint(1, 3))

        call_id = uid()
        started = ago(days=days_old, hours=random.randint(0, 12))

        col.insert_one({
            "call_id": call_id,
            "phone_number": f"+1{random.randint(2000000000, 9999999999)}",
            "customer": {"name": buyer[0], "number": f"+1{random.randint(2000000000, 9999999999)}"},
            "status": "completed",
            "started_at": started,
            "ended_at": started + timedelta(seconds=duration),
            "duration_seconds": duration,
            "summary": CALL_SUMMARIES[i % len(CALL_SUMMARIES)],
            "transcript": CALL_TRANSCRIPTS[i % len(CALL_TRANSCRIPTS)],
            "key_points": [
                f"Discussed {call_objections[0][1].lower()}",
                f"Buyer showed interest in {random.choice(['call coaching', 'proposal generation', 'CRM integration', 'email campaigns'])}",
                f"Next step: {random.choice(['Schedule demo', 'Send ROI deck', 'Start trial', 'Follow up next week'])}",
            ],
            "next_steps": [
                random.choice(["Schedule follow-up demo", "Send pricing comparison", "Share ROI calculator", "Set up pilot"]),
                random.choice(["Send case study", "Connect with technical team", "Prepare security overview"]),
            ],
            "recording_url": f"https://recordings.pravaha.ai/calls/{call_id}.mp3",
            "objection_summary": {
                "has_objection": True,
                "risk_level": risk,
                "objections": [{"type": o[0], "label": o[1], "evidence": f"Prospect expressed concerns about {o[1].lower()}"} for o in call_objections],
                "buying_signals": [{"type": s[0], "label": s[1], "evidence": s[1]} for s in call_signals],
                "questions": [random.choice(BUYER_QUESTIONS) for _ in range(random.randint(1, 3))],
                "action_items": ["Send follow-up email", "Schedule demo", "Prepare ROI analysis"],
                "recommended_next_step": random.choice(["Schedule demo", "Send trial invite", "Share case study", "Prepare enterprise proposal"]),
                "summary_text": f"Call with {buyer[0]} covered {', '.join(o[1] for o in call_objections)}. Overall risk: {risk}.",
            },
            "crm_note": f"Call with {buyer[0]} — {duration // 60}min. Discussed {call_objections[0][1]}. {random.choice(['Positive outlook.', 'Needs follow-up.', 'Strong interest.', 'Progressing to next stage.'])}",
            "crm_note_title": f"Sales Call — {buyer[0]}",
            "follow_up_actions": [
                f"Email {buyer[0]} the ROI summary",
                "Update deal stage in CRM",
            ],
            "buying_signals": [{"type": s[0], "label": s[1], "evidence": s[1]} for s in call_signals],
            "risk_level": risk,
            "recommended_next_step": "Schedule follow-up",
            "created_at": started,
            "rep_id": rep[0],
            "rep_email": rep[1],
        })
        created += 1

    print(f"  Calls: {created} created")


def seed_coaching_tips():
    """Create coaching tips linked to calls."""
    col = app_db["coaching_tips"]
    calls = list(app_db["calls"].find({}, {"call_id": 1, "rep_id": 1, "started_at": 1}))
    created = 0

    for call in calls:
        num_tips = random.randint(2, 4)
        tips = random.sample(COACHING_TIP_CONTENT, k=min(num_tips, len(COACHING_TIP_CONTENT)))
        for tip_type, subtype, content, evidence in tips:
            rep_id = call.get("rep_id", "admin")
            feedback = random.choice([None, None, "helpful", "helpful", "used_it", "not_relevant"])
            col.insert_one({
                "tip_id": uid(),
                "call_id": call["call_id"],
                "rep_id": rep_id,
                "type": tip_type,
                "subtype": subtype,
                "content": content,
                "evidence": evidence,
                "context": {"call_stage": random.choice(["opening", "discovery", "presentation", "objection_handling", "closing"])},
                "feedback": feedback,
                "feedback_by": rep_id if feedback else None,
                "feedback_at": ago(days=random.randint(0, 5)) if feedback else None,
                "timestamp": call.get("started_at", ago(days=5)) + timedelta(minutes=random.randint(1, 15)),
                "created_at": call.get("started_at", ago(days=5)),
            })
            created += 1

    print(f"  Coaching tips: {created} created")


def seed_coaching_playbook():
    """Create playbook entries."""
    col = app_db["coaching_playbook"]
    entries = [
        ("objection", 1, "Price Objection Handler", "When prospect says price is too high, use ROI framing",
         "pricing", "ROI reframe", "At $299/mo generating $2-8K additional revenue, Pravaha pays for itself with one deal."),
        ("objection", 2, "Competitor Displacement", "When prospect uses Gong/Chorus/Salesloft, differentiate on real-time",
         "competitor", "Feature differentiation", "Unlike post-call analytics, we coach IN the moment during live calls."),
        ("technique", 3, "Discovery First", "Always ask discovery questions before jumping into a demo",
         None, "Question-led selling", "What does your current sales process look like? Where do reps struggle most?"),
        ("technique", 4, "Champion Enablement", "When multiple stakeholders involved, arm your champion",
         None, "Stakeholder mapping", "Prepare ROI deck for CFO, security doc for IT, demo recording for the team."),
        ("closing", 5, "Assumptive Close", "Use assumptive language to advance to next step",
         None, "Assumptive close", "Should we schedule the onboarding for Monday or Wednesday?"),
        ("objection", 6, "Timing Objection", "Create urgency around the cost of delay",
         "timing", "Cost of delay", "Every month without AI coaching = deals lost to unhandled objections."),
        ("technique", 7, "Feel Felt Found", "Classic empathy framework for objection handling",
         None, "Empathy bridge", "I understand how you feel. Other customers felt the same way. What they found was..."),
        ("objection", 8, "Security Concerns", "Address data security proactively with compliance details",
         "security", "Compliance checklist", "SOC 2 Type II, AES-256 encryption, GDPR compliant, DPA available."),
    ]
    created = 0
    for cat, priority, title, desc, obj_type, technique, example in entries:
        col.update_one(
            {"title": title},
            {"$set": {
                "entry_id": uid(),
                "category": cat,
                "priority": priority,
                "title": title,
                "description": desc,
                "objection_type": obj_type,
                "technique": technique,
                "example": example,
                "updated_at": ago(days=random.randint(1, 20)),
            }},
            upsert=True,
        )
        created += 1
    print(f"  Coaching playbook: {created} entries")


def seed_email_campaigns():
    """Create email campaign records."""
    col = app_db["email_campaigns"]
    created = 0

    for i in range(15):
        rep = REP_NAMES[i % len(REP_NAMES)]
        buyer = BUYER_NAMES[i % len(BUYER_NAMES)]
        days_old = random.randint(1, 30)
        company = buyer[1].split("@")[1].split(".")[0].title()

        col.insert_one({
            "campaign_id": uid(),
            "rep_id": rep[0],
            "recipient_email": buyer[1],
            "subject": random.choice(EMAIL_SUBJECTS).format(company=company),
            "body_html": f"<p>Hi {buyer[0].split()[0]},</p><p>I wanted to follow up on our conversation about how Pravaha AI can help {company} improve sales performance.</p><p>Our customers typically see a 22% improvement in conversion rates within the first 90 days.</p><p>Would you be open to a quick 15-minute demo this week?</p><p>Best,<br/>{rep[2]}</p>",
            "status": random.choice(["sent", "sent", "sent", "scheduled", "draft"]),
            "created_at": ago(days=days_old),
            "sent_at": ago(days=days_old - 1) if random.random() > 0.2 else None,
        })
        created += 1

    print(f"  Email campaigns: {created} created")


def seed_chats():
    """Create chat session records."""
    col = app_db["chats"]
    created = 0

    chat_exchanges = [
        ("What does Pravaha AI do?", "Pravaha AI is an AI-powered sales automation platform that provides real-time call coaching, intelligent proposal generation, CRM integration, and mass email campaigns to help sales teams close more deals."),
        ("How much does it cost?", "We offer three plans: Starter at $99/mo for 1-3 users, Growth at $299/mo for up to 10 users, and Enterprise with custom pricing for unlimited users. All plans include a 14-day free trial."),
        ("Can it integrate with HubSpot?", "Yes! Our HubSpot integration provides bi-directional sync. Call summaries, notes, and next steps are automatically synced to HubSpot contacts. Deal stages update automatically after calls."),
        ("What ROI can I expect?", "Based on data from 120+ customers: +22% sales conversion rate, +18% average deal size, 40% faster ramp time for new reps, and proposal turnaround from 3 days to 15 minutes."),
        ("Is it secure?", "Absolutely. Pravaha AI is SOC 2 Type II certified, GDPR compliant, uses AES-256 encryption at rest and TLS 1.3 in transit. We never train models on your customer data. Enterprise plans include data residency options."),
    ]

    for i in range(8):
        sessions = []
        for j in range(random.randint(1, 3)):
            q, a = random.choice(chat_exchanges)
            sessions.append({
                "user": "AI",
                "message": a,
                "role": random.choice(["admin", "team", "user"]),
                "created_at": ago(days=random.randint(1, 20)),
            })
        col.insert_one({
            "sessions": sessions,
            "created_at": ago(days=random.randint(1, 25)),
        })
        created += 1

    print(f"  Chat sessions: {created} created")


def seed_automations():
    """Create automation workflow definitions and some runs."""
    auto_col = app_db["automations"]
    run_col = app_db["automation_runs"]
    created_auto = 0
    created_runs = 0

    automation_defs = [
        ("Post-Call Summary Generator", "summarize_transcript",
         "Automatically generates call summary, key points, and next steps after every call completes.",
         True, "interval", 5),
        ("AI Proposal Drafter", "draft_proposal",
         "Drafts a personalized proposal using call context and uploaded product documents.",
         True, "manual", None),
        ("CRM Note Publisher", "prepare_crm_note",
         "Prepares and pushes structured call notes to HubSpot after each call.",
         True, "interval", 10),
        ("Follow-Up Reminder", "trigger_reminder",
         "Sends a follow-up reminder to the rep if no action taken within 48 hours of a call.",
         True, "interval", 60),
        ("Manager Daily Brief", "manager_daily_brief",
         "Generates a daily briefing for sales managers with pipeline health, risks, and wins.",
         True, "interval", 1440),
    ]

    for name, atype, desc, enabled, mode, interval in automation_defs:
        auto_id = uid()
        auto_col.update_one(
            {"name": name},
            {"$set": {
                "automation_id": auto_id,
                "name": name,
                "type": atype,
                "description": desc,
                "enabled": enabled,
                "scope": {},
                "schedule": {
                    "mode": mode,
                    "interval_minutes": interval,
                },
                "config": {"retry_limit": 3, "retry_backoff_minutes": 5, "review_required": False},
                "created_by": "admin@pravaha.ai",
                "created_at": ago(days=60),
                "updated_at": ago(days=random.randint(1, 10)),
                "last_run_at": ago(hours=random.randint(1, 48)),
                "last_run_status": "success",
                "retry_count": 0,
                "runtime_status": "idle",
            }},
            upsert=True,
        )
        created_auto += 1

        # Create some runs
        for r in range(random.randint(3, 8)):
            started = ago(days=random.randint(1, 20), hours=random.randint(0, 12))
            run_col.insert_one({
                "run_id": uid(),
                "automation_id": auto_id,
                "automation_name": name,
                "automation_type": atype,
                "input": {"trigger": "scheduled"},
                "output": {"result": "Completed successfully"},
                "status": random.choice(["success", "success", "success", "failed"]),
                "error": None if random.random() > 0.15 else "Temporary API timeout",
                "triggered_by": "scheduler",
                "started_at": started,
                "completed_at": started + timedelta(seconds=random.randint(2, 30)),
                "finished_at": started + timedelta(seconds=random.randint(2, 30)),
                "retry_count": 0,
                "max_retries": 3,
                "review_required": False,
                "dead_lettered": False,
            })
            created_runs += 1

    print(f"  Automations: {created_auto} workflows, {created_runs} runs")


def seed_sync_log():
    """Create CRM sync log entries."""
    col = app_db["sync_log"]
    created = 0
    events = [
        ("call_summary_synced", "hubspot", "success"),
        ("contact_created", "hubspot", "success"),
        ("deal_stage_updated", "hubspot", "success"),
        ("proposal_shared", "hubspot", "success"),
        ("bulk_email_synced", "hubspot", "success"),
        ("contact_sync_failed", "hubspot", "failed"),
    ]

    for i in range(20):
        event, provider, status = random.choice(events)
        col.insert_one({
            "event": event,
            "provider": provider,
            "entity_id": uid()[:12],
            "status": status,
            "data": {"details": f"Synced {event.replace('_', ' ')}"},
            "error": "Rate limit exceeded" if status == "failed" else None,
            "created_at": ago(days=random.randint(0, 15), hours=random.randint(0, 23)),
        })
        created += 1

    print(f"  Sync log: {created} entries")


def seed_agent_actions():
    """Create agent action log entries."""
    col = app_db["agent_actions"]
    created = 0
    actions = [
        ("call_coach", "generate_tip", "Generated real-time coaching tip"),
        ("proposal_agent", "generate_proposal", "Generated proposal from documents"),
        ("email_agent", "draft_followup", "Drafted follow-up email"),
        ("crm_agent", "sync_notes", "Synced call notes to HubSpot"),
        ("intelligence_agent", "daily_brief", "Generated daily intelligence brief"),
        ("intelligence_agent", "next_best_action", "Computed next best action recommendations"),
    ]

    for i in range(25):
        agent, action, desc = random.choice(actions)
        col.insert_one({
            "action_id": uid(),
            "agent": agent,
            "action": action,
            "input": {"description": desc},
            "output": {"status": "completed"},
            "status": random.choice(["success", "success", "success", "success", "failed"]),
            "user_id": random.choice(REP_NAMES)[0],
            "metadata": {},
            "created_at": ago(days=random.randint(0, 20), hours=random.randint(0, 23)),
        })
        created += 1

    print(f"  Agent actions: {created} entries")


def seed_followup_config():
    """Set default follow-up configuration."""
    app_db["followup_config"].update_one(
        {"user_id": "admin@pravaha.ai"},
        {"$set": {
            "user_id": "admin@pravaha.ai",
            "enabled": True,
            "delay_hours": 48,
            "created_at": ago(days=60),
            "updated_at": ago(days=5),
        }},
        upsert=True,
    )
    print("  Follow-up config: set")


def seed_endpoints():
    """Create endpoint usage counters."""
    col = app_db["endpoints"]
    endpoints = [
        ("/chat/response", 142),
        ("/chat/coach", 87),
        ("/admin/analytics", 356),
        ("/admin/generate_proposal", 28),
        ("/admin/call", 64),
        ("/admin/send_bulk_email", 15),
        ("/admin/ingest", 8),
        ("/admin/coaching/stats", 93),
        ("/admin/intelligence/daily_brief", 45),
        ("/admin/intelligence/next_best_action", 67),
    ]
    for endpoint, count in endpoints:
        col.update_one(
            {"endpoint": endpoint},
            {"$set": {"endpoint": endpoint, "count": count}},
            upsert=True,
        )
    print(f"  Endpoint counters: {len(endpoints)} set")


def seed_revision_suggestions():
    """Create proposal revision suggestions."""
    col = app_db["proposal_revision_suggestions"]
    proposals = list(app_db["proposals"].find({}, {"proposal_id": 1}))
    created = 0

    suggestions = [
        ("Executive Summary", "Buyer asked about implementation timeline — add onboarding details",
         "Our dedicated Customer Success team ensures you're fully operational within 2 hours of signup, with a 30-day guided onboarding program."),
        ("Pricing", "Multiple questions about pricing flexibility — add monthly option callout",
         "All plans are available month-to-month with no long-term commitment. Annual billing saves 20%."),
        ("Security", "Buyer expressed data privacy concerns — strengthen security section",
         "Pravaha AI is SOC 2 Type II certified with AES-256 encryption at rest, TLS 1.3 in transit, and per-tenant data isolation."),
        ("ROI Section", "Add specific metrics from similar customer in same industry",
         "Companies in your industry using Pravaha AI have seen an average 28% improvement in conversion rates and 35% reduction in proposal turnaround time."),
    ]

    for proposal in proposals[:5]:
        for section, reason, text in random.sample(suggestions, k=random.randint(1, 3)):
            col.insert_one({
                "suggestion_id": uid(),
                "proposal_id": proposal["proposal_id"],
                "section": section,
                "reason": reason,
                "suggested_text": text,
                "source_questions": [random.choice(BUYER_QUESTIONS)],
                "created_by": "ai_agent",
                "status": random.choice(["pending", "pending", "applied", "dismissed"]),
                "created_at": ago(days=random.randint(1, 10)),
                "updated_at": ago(days=random.randint(0, 5)),
                "resolved_at": None,
            })
            created += 1

    print(f"  Revision suggestions: {created} created")


# ── Reset ─────────────────────────────────────────────────────────────────────

SEED_COLLECTIONS = [
    "proposals", "calls", "coaching_tips", "coaching_playbook",
    "email_campaigns", "chats", "automations", "automation_runs",
    "sync_log", "agent_actions", "endpoints", "onboarding",
    "followup_config", "proposal_revision_suggestions",
    "daily_briefs", "next_best_actions",
]

def reset_seed_data():
    """Drop all seeded collections (preserves users)."""
    print("\nResetting seed data...")
    for name in SEED_COLLECTIONS:
        app_db[name].drop()
        print(f"  Dropped {name}")
    # Only remove non-admin seeded users
    result = auth_db["users"].delete_many({
        "username": {"$in": [r[0] for r in REP_NAMES] + ["demo_user"]}
    })
    print(f"  Removed {result.deleted_count} seeded users (kept admin)")
    print("  Reset complete.\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed Pravaha with demo data")
    parser.add_argument("--reset", action="store_true", help="Drop seeded data before re-seeding")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("  Pravaha Seed Script")
    print(f"  Auth DB: {AUTH_DB}  |  App DB: {APP_DB}")
    print(f"{'='*60}\n")

    if args.reset:
        reset_seed_data()

    print("Seeding data...\n")
    seed_users()
    seed_onboarding()
    seed_proposals()
    seed_calls()
    seed_coaching_tips()
    seed_coaching_playbook()
    seed_email_campaigns()
    seed_chats()
    seed_automations()
    seed_sync_log()
    seed_agent_actions()
    seed_followup_config()
    seed_endpoints()
    seed_revision_suggestions()

    print(f"\n{'='*60}")
    print("  Seeding complete!")
    print(f"  Dashboard, Analytics, Coaching Hub, Proposals,")
    print(f"  Call Intelligence, Settings — all populated.")
    print(f"\n  Credentials:")
    print(f"    Admin:  admin / admin")
    print(f"    Team:   sarah_jones / team123  (or any rep)")
    print(f"    User:   demo_user / demo123")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
