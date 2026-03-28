# Pravaha — Implementation Plan
> **Status note**: This file is not authoritative. The live version is at the repo root: [`IMPLEMENTATION_PLAN.md`](../IMPLEMENTATION_PLAN.md).

**Goal**: Elevate Pravaha from prototype to a differentiated AI sales platform
**Duration**: 6–7 weeks
**Stack**: FastAPI + Next.js + MongoDB + Pinecone + VAPI + Twilio

---

## USP Summary (What We're Building)

| # | USP | Competitive Edge |
|---|-----|-----------------|
| 1 | Buyer-Facing Chat in Proposals | No competitor does this |
| 2 | Real-Time Sales Coaching During Calls | Only Outreach partially does this, badly |
| 3 | CRM Sync (HubSpot first) | Table-stakes; unlocks enterprise deals |
| 4 | Cross-Channel Intelligence Loop | No competitor connects all channels |
| 5 | Role-Based AI Personas | Unique UX for 3 different user types |
| 6 | 30-Minute Onboarding Wizard | Drift takes days; Pravaha takes 30 minutes |
| 7 | Transparent Pricing Page | Every competitor hides pricing |
| 8 | Agentic Revenue Ops Automation | OpenClaw-style internal operator across calls, proposals, CRM, and reminders |

---

## Phase 0 — Fix Existing Stubs (Pre-work, 2–3 days)

Before building new features, fix what's broken/incomplete in the prototype.

### 0.1 Complete Email Page
**File**: `frontend/src/app/dashboard/email/page.tsx`

**Tasks**:
- [ ] Build `EmailPage` component with recipient list input (comma-separated or paste)
- [ ] Subject line input
- [ ] Rich-text email body editor (use `react-quill` or `textarea` with markdown)
- [ ] Preview panel showing how email looks
- [ ] Send button calling `POST /admin/send_bulk_email`
- [ ] Response feedback: success count, failure list
- [ ] Add loading state and error handling

**Backend** (`routers/admin/`):
- [ ] Verify `POST /admin/send_bulk_email` returns proper `{sent, failed, results}` response
- [ ] Add email validation before sending
- [ ] Add rate limiting (max 500/batch)

---

### 0.2 Complete Voice Page
**File**: `frontend/src/app/dashboard/voice/page.tsx`

**Tasks**:
- [ ] Build `VoiceCall` component with phone number input
- [ ] Call script/context textarea
- [ ] "Start Call" button calling `POST /admin/call`
- [ ] Live call status indicator (polling `/admin/call_status?call_id=`)
- [ ] Call summary display after call ends (from `/admin/get_last_summary`)
- [ ] Call history list

**Backend**:
- [ ] Add `GET /admin/call_status?call_id=` endpoint that polls VAPI
- [ ] Ensure `get_last_summary` returns structured data (duration, key points, next steps)

---

### 0.3 Fix Broken UX Issues
- [ ] Fix text-to-speech toggle in chat (currently doesn't actually gate `speak()`)
- [ ] Add active route highlighting in `Sidebar.tsx`
- [ ] Enable "Agent Calls" and "Mass Mail" sidebar items (remove `opacity-70`)
- [ ] Fix admin detection (currently checks if email contains "admin" — use JWT role instead)
- [ ] Sanitize `dangerouslySetInnerHTML` in PDF page (use `DOMPurify`)
- [ ] Replace hardcoded backend URL with `NEXT_PUBLIC_API_URL` env variable everywhere

---

## Phase 1 — Role-Based AI Personas (Week 1)

**USP**: *"One platform, three completely different AI experiences"*

### What We're Building
Three distinct AI behaviors and UI experiences based on user role:
- **End Customer** (`USER` role): Friendly product Q&A bot, no jargon, CTA to book demo
- **Sales Rep** (`TEAM` role): Objection-handling coach, real-time tips, document-aware
- **Sales Manager** (`ADMIN` role): Deal health alerts, team performance summaries

---

### 1.1 Backend — Role-Aware Chat Prompts
**File**: `backend/utils/chatbot.py`

**Tasks**:
- [ ] Add `user_role` parameter to `ChatBot.get_response()`
- [ ] Create 3 system prompt templates:

```python
PROMPTS = {
    "USER": """You are pravaha, a friendly product assistant for {company_name}.
    Your goal: answer questions clearly, avoid jargon, and guide the user
    toward booking a demo or talking to a sales rep.
    Context: {context}""",

    "TEAM": """You are pravaha, a real-time sales coach.
    The sales rep is on a call or preparing for one.
    Detect objections, suggest responses, recommend relevant documents.
    Keep responses concise — max 2 sentences.
    Context from our documents: {context}""",

    "ADMIN": """You are pravaha, a sales intelligence assistant for the manager.
    Summarize deal health, flag risks, surface team performance insights.
    Reference data from analytics and recent call summaries.
    Context: {context}"""
}
```

- [ ] Inject role-specific prompt based on JWT token role
- [ ] Add `company_name` to context (from `.env` or settings)

---

### 1.2 Backend — Role-Aware Chat Endpoint
**File**: `backend/routers/chat/response.py`

**Tasks**:
- [ ] Extract user role from bearer token in `/chat/response`
- [ ] Pass role to `ChatBot.get_response(user_input, session_id, role=user_role)`
- [ ] Add `role` field to response: `{"response": "...", "role": "TEAM", ...}`

---

### 1.3 Frontend — Role-Based Chat UI
**File**: `frontend/src/app/chat/page.tsx`

**Tasks**:
- [ ] Read role from JWT (decode `accessToken` from localStorage)
- [ ] Render different UI per role:
  - `USER`: Clean minimal chat, "Book a Demo" CTA button
  - `TEAM`: Chat + collapsible "Coaching Tips" sidebar
  - `ADMIN`: Chat + "Team Insights" panel with quick stats
- [ ] Different placeholder text per role:
  - USER: "Ask me anything about our product..."
  - TEAM: "What objection are you facing?"
  - ADMIN: "Ask about deal health, team performance..."

---

### 1.4 Complete Sales Team Chatbot Page
**File**: `frontend/src/app/salesteam_chatbot/page.tsx`

**Tasks**:
- [ ] Build full chat interface (copy from `/chat/page.tsx`, customize for TEAM role)
- [ ] Add "Quick Objection Templates" sidebar:
  - "Too expensive"
  - "Using a competitor"
  - "Not the right time"
  - "Need to think about it"
- [ ] One-click insert template into chat input
- [ ] Display relevant document snippets alongside AI response

---

## Phase 2 — Buyer-Facing Chat in Proposals (Week 2)

**USP**: *"Proposals that answer buyer questions — automatically"*

### What We're Building
1. Each generated proposal gets a unique shareable public URL
2. Buyer opens the URL, reads the proposal, sees an embedded chat widget
3. Buyer provides name + email (lead capture), then chats freely
4. Admin sees a live feed of all buyer questions and pravaha's answers
5. Admin gets notified when a buyer engages with a proposal

---

### 2.1 Backend — Proposal ID & Public Storage
**File**: `backend/routers/admin/generate_proposal.py`

**Tasks**:
- [ ] Generate UUID for each proposal on creation
- [ ] Store proposal metadata in MongoDB `proposal` collection:
```python
{
  "proposal_id": "uuid-v4",
  "created_by": "admin_username",
  "created_at": datetime,
  "documents_used": ["doc1.pdf"],
  "html_content": "<html>...",
  "status": "active",
  "views": 0,
  "buyer_sessions": []
}
```
- [ ] Add `GET /proposal/[proposal_id]` — public endpoint (no auth) that returns HTML
- [ ] Add `GET /admin/proposals` — list all proposals with engagement stats

---

### 2.2 Backend — Public Buyer Chat Endpoint
**File**: `backend/routers/chat/` (new file: `buyer_chat.py`)

**Tasks**:
- [ ] Create `POST /proposal/[proposal_id]/chat` — **no authentication required**
- [ ] Request body:
```python
{
  "buyer_name": "John Smith",
  "buyer_email": "john@company.com",
  "message": "What's the implementation timeline?",
  "session_id": "browser-generated-uuid"
}
```
- [ ] Load proposal context from MongoDB by `proposal_id`
- [ ] Use same `ChatBot` class but with `USER` role prompt
- [ ] Store buyer conversation in MongoDB:
```python
# In proposal document
"buyer_sessions": [{
  "session_id": "...",
  "buyer_name": "John Smith",
  "buyer_email": "john@company.com",
  "messages": [{"role": "user", "content": "...", "timestamp": ...}],
  "started_at": datetime
}]
```
- [ ] Return `{"response": "...", "session_id": "..."}`

---

### 2.3 Backend — Buyer Engagement Tracking
**File**: `backend/routers/admin/` (add to existing or new `proposals.py`)

**Tasks**:
- [ ] `POST /proposal/[proposal_id]/view` — increment view counter, log timestamp + IP
- [ ] `GET /admin/proposal/[proposal_id]/engagement` — return:
```python
{
  "proposal_id": "...",
  "views": 12,
  "unique_buyers": 3,
  "buyer_sessions": [
    {
      "buyer_name": "John Smith",
      "buyer_email": "john@company.com",
      "questions_asked": 4,
      "last_active": datetime,
      "messages": [...]
    }
  ],
  "most_asked_questions": ["pricing", "timeline", "integration"]
}
```

---

### 2.4 Frontend — Public Proposal Page
**File**: `frontend/src/app/proposal/[id]/page.tsx` (new page)

**Tasks**:
- [ ] Fetch proposal HTML from `GET /proposal/[proposal_id]`
- [ ] Render proposal content (sanitized HTML)
- [ ] Track view on page load (`POST /proposal/[id]/view`)
- [ ] Show "Lead Capture Modal" on first visit:
  - Name input (required)
  - Email input (required)
  - "Start Reading" button
  - Store `{name, email}` in localStorage for session
- [ ] Render floating chat widget (bottom-right corner):
  - Chat bubble button (collapsed by default)
  - Expands to chat window
  - Shows "Ask pravaha about this proposal"
  - Chat history persisted in localStorage for session
- [ ] Calls `POST /proposal/[id]/chat` with buyer credentials
- [ ] Proposal branding: company logo, pravaha watermark (bottom)

---

### 2.5 Frontend — Admin Proposal Engagement Dashboard
**File**: `frontend/src/app/dashboard/proposals/page.tsx` (new page)

**Tasks**:
- [ ] List all proposals with:
  - Title, created date, status (active/archived)
  - View count badge
  - Unique buyer count
  - "Copy Link" button → copies `/proposal/[id]` to clipboard
  - "View Engagement" button
- [ ] Engagement detail view per proposal:
  - Buyer list with name, email, question count, last active
  - Timeline of buyer activity
  - Full conversation transcript per buyer
  - "Most Asked Questions" word cloud or list
- [ ] Add "Proposals" to Sidebar navigation

---

## Phase 3 — Real-Time Sales Coaching (Week 3)

**USP**: *"Your AI coach whispers the right answer while you're on the call"*

### What We're Building
1. Sales rep initiates a VAPI call from the voice page
2. VAPI sends real-time transcript chunks via webhook
3. Backend processes each chunk with LLM to detect objections/opportunities
4. Coaching tip is pushed to the rep's screen via WebSocket in real-time
5. Rep sees a live overlay: "💡 Buyer mentioned budget — show ROI slide"

---

### 3.1 Backend — VAPI Webhook Receiver
**File**: `backend/routers/admin/` (new file: `coaching.py`)

**Tasks**:
- [ ] Create `POST /webhook/vapi` — public endpoint for VAPI to POST to
- [ ] Parse VAPI webhook payload:
```python
{
  "call_id": "vapi-call-id",
  "transcript": "...latest utterance...",
  "speaker": "customer",  # or "assistant"
  "timestamp": "...",
  "full_transcript_so_far": "..."
}
```
- [ ] Only process when `speaker == "customer"` (buyer speaking)
- [ ] Store full transcript in MongoDB `calls` collection
- [ ] Trigger coaching analysis (async, non-blocking)

---

### 3.2 Backend — Coaching LLM Analysis
**File**: `backend/utils/coaching.py` (new file)

**Tasks**:
- [ ] Create `CoachingEngine` class
- [ ] Prompt template for objection detection:
```python
COACHING_PROMPT = """
You are a real-time sales coach. Analyze this latest customer statement:
"{latest_utterance}"

Full conversation so far: {transcript}
Available documents: {document_context}

Detect if there is:
1. A price/budget objection
2. A competitor mention
3. A timeline concern
4. A feature question
5. A positive buying signal
6. A request for more information

If detected, respond with a JSON coaching tip:
{
  "type": "objection|opportunity|question|signal",
  "detected": "What you detected in one sentence",
  "suggested_response": "What the rep should say (max 2 sentences)",
  "relevant_document": "Which doc/section to reference (if any)",
  "urgency": "high|medium|low"
}

If nothing significant detected, return: {"type": "none"}
"""
```
- [ ] Call LLM (Groq `llama-3.1-8b-instant` for speed — low latency critical here)
- [ ] Parse JSON response
- [ ] Push coaching tip to rep via WebSocket (see 3.3)

---

### 3.3 Backend — WebSocket for Live Coaching
**File**: `backend/main.py` + `backend/routers/admin/coaching.py`

**Tasks**:
- [ ] Add WebSocket endpoint: `WS /ws/coaching/[call_id]`
- [ ] Store active WebSocket connections in memory dict:
```python
active_coaching_sessions: Dict[str, WebSocket] = {}
```
- [ ] When VAPI webhook fires, look up call_id → push coaching tip over WebSocket
- [ ] Handle disconnect gracefully
- [ ] Add FastAPI WebSocket support:
```python
from fastapi import WebSocket
@app.websocket("/ws/coaching/{call_id}")
async def coaching_websocket(websocket: WebSocket, call_id: str):
    await websocket.accept()
    active_coaching_sessions[call_id] = websocket
    ...
```

---

### 3.4 Frontend — Live Coaching Overlay
**File**: `frontend/src/app/dashboard/voice/page.tsx`

**Tasks**:
- [ ] On "Start Call" click:
  - Call `POST /admin/call`, receive `call_id`
  - Open WebSocket connection to `WS /ws/coaching/[call_id]`
- [ ] Render coaching overlay panel (right side of screen):
  - Call status indicator (active/ended)
  - Live transcript display (scrolling)
  - Coaching tips feed (newest on top):
```
💡 Budget Objection Detected
Buyer: "This seems expensive..."
Suggested: "Let me show you the ROI — most customers see
            3x return within 6 months."
[Reference: pricing-guide.pdf > Page 4]
```
- [ ] Color-code by type:
  - 🔴 Objection (red)
  - 🟢 Buying signal (green)
  - 🔵 Question (blue)
  - 🟡 Opportunity (yellow)
- [ ] "Copy Tip" button on each coaching card
- [ ] Tip notification badge when panel is collapsed
- [ ] Call ends → show full summary + all coaching tips used

---

### 3.5 Backend — Configure VAPI Webhook
**File**: `backend/utils/call.py`

**Tasks**:
- [ ] When initiating call via VAPI API, set webhook URL:
```python
payload = {
  "phoneNumberId": TWILIO_PHONE_ID,
  "customer": {"number": phone_number},
  "assistant": {...},
  "serverUrl": f"{API_BASE_URL}/webhook/vapi",  # ← add this
  "serverUrlSecret": VAPI_WEBHOOK_SECRET       # ← add this
}
```
- [ ] Add `VAPI_WEBHOOK_SECRET` to `.env` for webhook signature verification
- [ ] Verify webhook signature on every incoming request (security)

---

## Phase 4 — CRM Sync: HubSpot (Week 4)

**USP**: *"Zero double data entry — pravaha updates your CRM automatically"*

### What We're Building
1. Admin connects their HubSpot account (OAuth)
2. pravaha automatically:
   - Creates a HubSpot **Contact** when a buyer opens a proposal and submits name/email
   - Creates a HubSpot **Deal** when a proposal is generated
   - Logs a HubSpot **Activity/Note** when a call is completed (with summary)
   - Logs a HubSpot **Activity** when a bulk email is sent
3. Admin can see sync status in dashboard

---

### 4.1 Backend — HubSpot OAuth Integration
**File**: `backend/routers/admin/crm.py` (new file)

**Tasks**:
- [ ] Add HubSpot app credentials to `.env`:
```
HUBSPOT_CLIENT_ID=...
HUBSPOT_CLIENT_SECRET=...
HUBSPOT_REDIRECT_URI=https://your-backend.com/crm/hubspot/callback
```
- [ ] `GET /crm/hubspot/connect` — redirect to HubSpot OAuth consent page
- [ ] `GET /crm/hubspot/callback` — exchange code for access+refresh tokens
- [ ] Store tokens in MongoDB `integrations` collection:
```python
{
  "user_id": "admin_username",
  "provider": "hubspot",
  "access_token": "...",
  "refresh_token": "...",
  "expires_at": datetime,
  "portal_id": "...",
  "connected_at": datetime
}
```
- [ ] `GET /crm/status` — return `{connected: true, provider: "hubspot", portal_id: "..."}`
- [ ] `DELETE /crm/hubspot/disconnect` — remove tokens
- [ ] Token refresh middleware (auto-refresh when expired)

---

### 4.2 Backend — HubSpot Sync Engine
**File**: `backend/utils/hubspot.py` (new file)

**Tasks**:
- [ ] Create `HubSpotSync` class with methods:

```python
class HubSpotSync:
    def __init__(self, access_token: str)

    async def create_contact(self, name: str, email: str,
                              company: str = None) -> str:
        # POST to HubSpot Contacts API
        # Returns HubSpot contact ID

    async def create_deal(self, title: str, proposal_id: str,
                           contact_id: str = None) -> str:
        # POST to HubSpot Deals API
        # Returns HubSpot deal ID

    async def log_call_activity(self, contact_id: str,
                                  call_summary: str,
                                  duration_seconds: int) -> None:
        # POST to HubSpot Engagements API (type: CALL)

    async def log_email_activity(self, contact_ids: List[str],
                                   subject: str, body: str) -> None:
        # POST to HubSpot Engagements API (type: EMAIL)

    async def update_deal_stage(self, deal_id: str,
                                  stage: str) -> None:
        # PATCH to HubSpot Deals API
```

---

### 4.3 Backend — Sync Triggers
Wire up HubSpot sync at the right points in existing flows:

**File**: `backend/routers/admin/generate_proposal.py`
- [ ] After proposal is generated → `hubspot.create_deal(title, proposal_id)`
- [ ] Store returned `hubspot_deal_id` in MongoDB proposal document

**File**: `backend/routers/chat/buyer_chat.py`
- [ ] On first buyer message (new session) → `hubspot.create_contact(name, email)`
- [ ] Store returned `hubspot_contact_id` in buyer session
- [ ] Associate contact with deal if `proposal_id` is known

**File**: `backend/utils/call.py`
- [ ] After call ends and summary is ready → `hubspot.log_call_activity(...)`

**File**: `backend/utils/bulkEmailSend.py`
- [ ] After bulk email sent → `hubspot.log_email_activity(...)`

---

### 4.4 Backend — Sync Status & Logs
**File**: `backend/routers/admin/crm.py`

**Tasks**:
- [ ] `GET /crm/sync-log` — return recent sync events:
```python
[
  {
    "event": "contact_created",
    "hubspot_id": "12345",
    "data": {"name": "John", "email": "john@co.com"},
    "timestamp": datetime,
    "status": "success"
  },
  ...
]
```
- [ ] Log all sync events to MongoDB `sync_log` collection
- [ ] Log failures with error message for debugging

---

### 4.5 Frontend — CRM Integration Settings Page
**File**: `frontend/src/app/dashboard/settings/page.tsx` (new page)

**Tasks**:
- [ ] "Integrations" section:
  - HubSpot card with logo
  - Connected status badge (green/red)
  - "Connect HubSpot" button → redirects to `/crm/hubspot/connect`
  - "Disconnect" button (when connected)
  - Shows portal ID and connection date
- [ ] "Sync Log" table:
  - Recent 20 sync events
  - Event type, entity, status, timestamp
  - Error message on failure rows
- [ ] "Sync Settings" toggles:
  - ☑ Auto-create contacts when buyer opens proposal
  - ☑ Auto-create deals when proposal is generated
  - ☑ Log call summaries as HubSpot activities
  - ☑ Log bulk emails as HubSpot activities
- [ ] Add "Settings" to Sidebar navigation

---

## Phase 5 — Cross-Channel Intelligence Loop (Week 5)

**USP**: *"Every channel makes every other channel smarter"*

### What We're Building
Data flows across all 4 channels (Chat → Email → Calls → Proposals):
- Call transcripts inform proposal content
- Buyer chat questions adapt proposal wording
- Email click patterns personalize AI chat tone
- Proposal engagement signals trigger follow-up emails

---

### 5.1 Call → Proposal Intelligence
**File**: `backend/routers/admin/generate_proposal.py`

**Tasks**:
- [ ] Add `GET /admin/call_insights` endpoint:
  - Pull last 5 call summaries from MongoDB
  - Extract: common objections, frequently asked questions, positive signals
  - Return structured insights
- [ ] In proposal generation prompt, inject call insights:
```python
PROPOSAL_PROMPT = """
Generate a sales proposal based on these documents.

Recent call insights:
- Common objections raised: {objections}
- Questions frequently asked: {faq}
- What prospects responded positively to: {positive_signals}

Use these insights to proactively address objections and
highlight the points prospects care most about.

Documents: {document_summaries}
"""
```
- [ ] Add toggle in proposal generation: "Include call insights" (on by default)

---

### 5.2 Buyer Chat → Proposal Adaptation
**File**: `backend/routers/admin/proposals.py`

**Tasks**:
- [ ] `POST /admin/proposal/[id]/regenerate-section` endpoint:
  - Input: section name (e.g., "pricing", "timeline")
  - Pulls all buyer questions related to that section
  - Re-generates that section to better address the questions
  - Updates proposal HTML in MongoDB
- [ ] Background job: after 5+ buyer questions on same topic → alert admin:
  - "3 buyers asked about implementation timeline — consider updating that section"

---

### 5.3 Email → Chat Personalization
**File**: `backend/utils/chatbot.py`

**Tasks**:
- [ ] `GET /admin/email_insights` endpoint:
  - Pull email send history from MongoDB
  - Track which subject lines had high open rates (if tracking pixel added)
  - Return: top-performing messaging themes
- [ ] Inject email insights into TEAM/USER chat context:
```python
# In ChatBot prompt
"Recent email campaigns that resonated: {email_themes}
Align your tone and messaging with what's been working."
```

---

### 5.4 Proposal Engagement → Email Trigger
**File**: `backend/routers/admin/proposals.py`

**Tasks**:
- [ ] Background task: when buyer hasn't engaged with proposal for 48 hours → trigger:
  - `POST /admin/send_bulk_email` with auto-generated follow-up email:
```
Subject: "Still have questions about [proposal title]?"
Body: "Hi {buyer_name}, I noticed you had a chance to review our proposal.
       pravaha noticed you asked about {top_question}. Here's a quick answer..."
```
- [ ] Admin can configure: enable/disable auto-follow-up, delay (24h/48h/72h)
- [ ] Show "Follow-up scheduled" badge on proposal engagement page

---

### 5.5 OpenClaw-Style Agent Actions Layer
**USP**: *"An internal AI operator that takes sales ops work off the rep's plate"*

Use an OpenClaw-like sidecar agent for internal workflows only. The agent should not replace the core app backend or public buyer chat. It should call approved FastAPI tools and log every action.

**Architecture**:
- [ ] Run agent runtime as a sidecar service behind the existing FastAPI app
- [ ] Expose narrow internal tools only:
  - `get_call_summary(call_id)`
  - `create_crm_note(contact_id, deal_id, body)`
  - `get_proposal_buyer_questions(proposal_id)`
  - `save_proposal_revision_suggestion(proposal_id, suggestion)`
  - `get_rep_activity(rep_id)`
  - `get_manager_daily_metrics(manager_id)`
  - `schedule_followup_reminder(...)`
- [ ] Add `agent_actions` collection in MongoDB for audit log:
```python
{
  "agent": "revenue_ops",
  "action": "create_crm_note",
  "input": {...},
  "output": {...},
  "status": "success",
  "created_at": datetime
}
```
- [ ] Restrict agent tools to internal users only; no buyer-facing direct access

---

### 5.6 Call Transcript → Objection Summary + CRM Note
**Files**: `backend/utils/call.py`, `backend/utils/coaching.py`, `backend/utils/hubspot.py`

**Tasks**:
- [ ] After call completion, generate structured objection summary:
```python
{
  "objections": ["pricing", "timeline"],
  "buying_signals": ["asked about onboarding"],
  "risks": ["currently using competitor"],
  "recommended_followup": "Send ROI case study and pricing breakdown"
}
```
- [ ] Convert that summary into a CRM-ready note body
- [ ] Auto-log the CRM note against the matched contact/deal
- [ ] Store both objection summary and CRM note text in MongoDB for reuse in proposals and manager reports
- [ ] Add "Copy CRM Note" button in call summary UI for manual override

---

### 5.7 Buyer Chat → Proposal Revision Suggestions
**Files**: `backend/routers/admin/proposals.py`, `frontend/src/app/dashboard/proposals/page.tsx`

**Tasks**:
- [ ] Analyze buyer chat threads by proposal and cluster repeated questions
- [ ] Generate section-level proposal revision suggestions:
  - "Timeline section needs clearer implementation milestones"
  - "Pricing section should address setup fees explicitly"
- [ ] Store suggestions separately from live proposal HTML so admins can review before applying
- [ ] Add admin UI panel:
  - Suggested section
  - Reason based on buyer questions
  - Proposed replacement copy
  - "Apply suggestion" / "Dismiss" actions
- [ ] Track which suggestions led to improved engagement

---

### 5.8 Rep Next-Best-Action Recommendations
**Files**: `backend/routers/admin/`, `frontend/src/app/chat/page.tsx`, `frontend/src/app/dashboard/page.tsx`

**Tasks**:
- [ ] Build `GET /admin/next_best_action?rep_id=` endpoint
- [ ] Combine call outcomes, proposal engagement, email activity, and CRM stage to rank the next recommended step
- [ ] Recommendation output:
```python
{
  "rep_id": "...",
  "deal_id": "...",
  "action": "Send follow-up with ROI calculator",
  "why": "Buyer raised budget concern and reopened proposal twice today",
  "urgency": "high"
}
```
- [ ] Show next-best-action cards in rep chat sidebar and dashboard home
- [ ] Add one-click actions where safe:
  - draft follow-up email
  - open proposal
  - open CRM record

---

### 5.9 Manager Daily Brief
**Files**: `backend/routers/admin/`, `frontend/src/app/dashboard/page.tsx`

**Tasks**:
- [ ] Build daily brief generator that aggregates:
  - proposal views and buyer questions
  - calls completed and objection patterns
  - bulk email activity and response signals
  - at-risk or high-momentum deals
- [ ] Add `GET /admin/daily_brief` endpoint returning both summary text and structured metrics
- [ ] Show manager brief card on ADMIN dashboard with:
  - today's top risks
  - top opportunities
  - reps needing attention
  - deals most likely to move
- [ ] Add export/share actions: copy summary, email brief, save to CRM note/log

---

## Phase 6 — Onboarding Wizard (Week 5–6)

**USP**: *"From signup to first AI response in under 30 minutes"*

### What We're Building
A guided setup flow that new admins go through:
1. Company info setup
2. Upload 2–3 product documents
3. AI trains automatically (ingest)
4. Test the chat
5. Share first proposal link

---

### 6.1 Backend — Onboarding State Tracking
**File**: `backend/utils/database.py`

**Tasks**:
- [ ] Add `onboarding` collection to MongoDB:
```python
{
  "user_id": "admin_username",
  "completed_steps": ["company_info", "docs_uploaded", "ai_trained"],
  "current_step": "test_chat",
  "completed_at": None,
  "company_name": "Acme Corp",
  "company_description": "...",
  "created_at": datetime
}
```
- [ ] `GET /onboarding/status` — return current step and completed steps
- [ ] `POST /onboarding/complete-step` — mark a step done
- [ ] `POST /onboarding/company-info` — save company name/description

---

### 6.2 Frontend — Onboarding Flow
**File**: `frontend/src/app/onboarding/page.tsx` (new page)

**Tasks**:
- [ ] Redirect new admins here after first login (check `onboarding.completed_at == null`)
- [ ] Step 1 — Company Info:
  - Company name, description, industry, website
  - Persona: "Who uses your product?" (checkboxes)
- [ ] Step 2 — Upload Documents:
  - Drag & drop PDF upload (reuse existing component)
  - Min 1, recommended 3 documents
  - "These will train your AI" helper text
- [ ] Step 3 — Train AI:
  - Auto-trigger `/admin/ingest` on entering step
  - Progress bar with steps: "Loading PDFs → Splitting text → Creating embeddings → Indexing"
  - Estimated time (30–60 seconds)
- [ ] Step 4 — Test Chat:
  - Mini embedded chat window
  - Suggested test question: "What does [company] do?"
  - "Looks good! Continue" button
- [ ] Step 5 — Share Proposal:
  - "Generate your first proposal" button
  - Copy shareable link
  - "Invite your team" email input
- [ ] Progress bar at top: Step 1/5, 2/5, etc.
- [ ] Skip button (for returning users)

---

## Phase 7 — Polish & Remaining USPs (Week 6–7)

### 7.1 Transparent Pricing Page
**File**: `frontend/src/app/pricing/page.tsx` (extend existing pricing section)

**Tasks**:
- [ ] Full dedicated pricing page at `/pricing`
- [ ] 3 tiers (no hidden fees, all inclusive):
  - **Starter** ($49/user/month): Chat, proposals, email
  - **Growth** ($99/user/month): + Voice calls, CRM sync, coaching
  - **Enterprise** (Custom): + White-label, dedicated support, compliance tools
- [ ] Feature comparison table
- [ ] "No credits. No surprises." tagline prominently displayed
- [ ] FAQ section: "What counts as a call?", "Is HubSpot included?", etc.
- [ ] Free trial CTA (14-day trial, no credit card)

---

### 7.2 Mobile Responsiveness Audit
**Files**: All dashboard pages

**Tasks**:
- [ ] Audit all dashboard pages on 375px (iPhone SE) and 768px (iPad)
- [ ] Fix sidebar: convert to bottom navigation on mobile
- [ ] Fix analytics grid: stack to 1-column on mobile
- [ ] Fix chat page: ensure input stays above keyboard
- [ ] Fix voice page: large tap targets for call controls
- [ ] Test Kanban board: ensure it works on touch devices

---

### 7.3 Proposal Engagement Analytics Widget
**File**: `frontend/src/components/analytics/`

**Tasks**:
- [ ] New widget: `proposal-engagement.tsx`
  - Shows: proposals sent, total views, unique buyers, avg questions asked
  - Trend sparkline (7-day)
- [ ] Add to dashboard grid
- [ ] Update `/admin/analytics` endpoint to include proposal engagement stats

---

### 7.4 Global Search
**File**: `frontend/src/app/dashboard/` (add to layout)

**Tasks**:
- [ ] CMD+K search overlay
- [ ] Search across: documents, proposals, call summaries, leads
- [ ] Backend: `GET /search?q=query&types=docs,proposals,calls`
- [ ] Uses existing Pinecone index for semantic search

---

### 7.5 Background Automations
**USP**: *"The platform keeps working after the rep closes the tab"*

**Files**: `backend/routers/admin/`, `backend/utils/`, optional sidecar worker service

**Tasks**:
- [ ] Add scheduler/worker layer for recurring and event-driven automations
- [ ] Core automations to ship first:
  - summarize transcripts after every completed call
  - draft proposal first pass from selected docs + recent call insights
  - prepare CRM notes after calls and proposal engagement spikes
  - trigger reminder tasks for stale proposals, unreplied buyers, and overdue rep follow-ups
- [ ] Add automation definitions stored in MongoDB:
```python
{
  "name": "manager_daily_brief",
  "trigger": "daily_08_30",
  "enabled": True,
  "scope": {"manager_id": "..."},
  "last_run_at": datetime,
  "last_status": "success"
}
```
- [ ] Add retry policy, dead-letter logging, and admin-visible run history
- [ ] Add settings UI to enable/disable each automation and choose timing
- [ ] Keep all automation outputs reviewable before destructive actions

---

## Technical Infrastructure (Throughout)

### Environment Variables to Add
```bash
# CRM
HUBSPOT_CLIENT_ID=
HUBSPOT_CLIENT_SECRET=
HUBSPOT_REDIRECT_URI=

# Webhooks
VAPI_WEBHOOK_SECRET=
API_BASE_URL=https://your-backend.onrender.com

# App
COMPANY_NAME=pravaha
JWT_SECRET=your-secure-random-key  # Move from hardcoded "mysecretkey"

# Frontend
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
NEXT_PUBLIC_APP_URL=https://your-frontend.vercel.app
```

### MongoDB Collections to Add
```
integrations    → CRM OAuth tokens
sync_log        → CRM sync event history
calls           → Full call transcripts + coaching tips
onboarding      → User onboarding state
buyer_sessions  → (already in proposals, formalize schema)
agent_actions   → internal agent tool audit trail
automations     → recurring/event-driven workflow definitions
automation_runs → execution history and failures
```

### Security Fixes (High Priority)
- [ ] Move `JWT_SECRET` from hardcoded `"mysecretkey"` to env var
- [ ] Move `SessionMiddleware` secret to env var
- [ ] Add `DOMPurify` sanitization to all `dangerouslySetInnerHTML` usages
- [ ] Move `accessToken` from `localStorage` to `httpOnly` cookie (XSS prevention)
- [ ] Add VAPI webhook signature verification

---

## Dependency Additions

### Backend (`requirements_fixed.txt`)
```
hubspot-api-client>=8.0.0     # HubSpot CRM integration
websockets>=12.0               # WebSocket support
python-multipart>=0.0.9        # Already likely present
apscheduler>=3.10.0            # Background jobs (follow-up emails)
celery>=5.4.0                  # Optional distributed worker for agent automations
redis>=5.0.0                   # Optional broker/cache for jobs and locks
```

### Frontend (`package.json`)
```json
{
  "dompurify": "^3.0.0",        // HTML sanitization
  "@types/dompurify": "^3.0.0",
  "react-quill": "^2.0.0",     // Rich text editor for emails
  "js-cookie": "^3.0.5",       // Cookie management
  "@types/js-cookie": "^3.0.0"
}
```

---

## Week-by-Week Timeline

| Week | Phase | Deliverables |
|------|-------|-------------|
| **Week 1** | Phase 0 + 1 | Fix stubs, role-based AI personas |
| **Week 2** | Phase 2 | Buyer-facing chat in proposals |
| **Week 3** | Phase 3 | Real-time sales coaching (WebSocket) |
| **Week 4** | Phase 4 | HubSpot CRM sync |
| **Week 5** | Phase 5 | Cross-channel loop + agent actions |
| **Week 6** | Phase 6 + 7 | Onboarding wizard + background automations + polish |
| **Week 7** | Buffer | Testing, bug fixes, demo prep |

---

## Feature Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Fix stubs (Email, Voice) | High | Low | 🔴 Do first |
| Fix security issues | High | Low | 🔴 Do first |
| Role-based AI personas | High | Medium | 🟠 Week 1 |
| Buyer-facing chat | Very High | Medium | 🟠 Week 2 |
| Real-time coaching | Very High | High | 🟠 Week 3 |
| HubSpot CRM sync | High | High | 🟡 Week 4 |
| Onboarding wizard | Medium | Medium | 🟡 Week 5 |
| Cross-channel loop | High | High | 🟡 Week 5 |
| Agent actions + automations | Very High | High | 🟡 Week 5-6 |
| Pricing page | Medium | Low | 🟢 Week 6 |
| Mobile audit | Medium | Medium | 🟢 Week 6 |
| Global search | Low | Medium | 🟢 Week 6 |

---

## How to Use This Plan

1. **Start with Phase 0** — get a stable foundation before adding features
2. **Each phase is independent** — can be worked on in parallel by multiple devs
3. **Backend tasks** are listed before Frontend tasks within each phase
4. **Checkbox format** — check off `[ ]` items as you complete them
5. **Each phase builds on the previous** — don't skip phases

---

*Last Updated: March 17, 2026*
*Based on: Prototype analysis + Competitive research across 10 tools*
*Target: Mid-market SaaS sales teams (50–200 reps)*
