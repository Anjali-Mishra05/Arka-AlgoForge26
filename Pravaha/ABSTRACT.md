# AI-Powered Intelligent Sales Automation Platform
## (End-to-End Sales Intelligence & Execution Engine)

**Project Name:** Pravaha
**Team:** ARKA

---

## 1. Idea Overview:

Sales teams across SaaS companies face severe challenges in managing the end-to-end sales cycle — from prospecting and outreach to proposal generation and deal closure. Current sales workflows suffer from **fragmented tool stacks** (separate tools for email, calls, CRM, proposals), **manual proposal creation** (often taking 2–5 days per RFP), **zero cross-channel learning** (call insights don't inform emails; chat data doesn't improve proposals), and **high rep onboarding time** (3+ months on enterprise platforms like Salesforce/Outreach).

This project proposes a **SaaS platform for AI-powered sales automation**, designed for SaaS sales teams of any size — from SMBs to enterprise. The platform enables sales reps, managers, and end-customers to interact through an **AI-driven conversational interface** backed by **RAG (Retrieval Augmented Generation)** over company documents. Using **LangChain for orchestration, Pinecone for vector search, Groq/OpenAI LLMs for generation**, and **VAPI + Twilio for voice automation**, the system ensures faster deal cycles, intelligent proposal generation, and real-time sales coaching.

The solution transforms reactive, manual sales operations into a **proactive, AI-driven, cross-channel sales intelligence engine** — applicable to B2B SaaS companies, agencies, and professional services firms targeting mid-market and enterprise customers.

---

## 2. Implementation Plan:

### System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         END USERS                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐                   │
│  │  Sales Rep    │  │ Sales Manager│  │  Buyer/Lead   │                   │
│  │  (TEAM role)  │  │ (ADMIN role) │  │  (USER role)  │                   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘                   │
└─────────┼─────────────────┼─────────────────┼────────────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    FRONTEND — Next.js 16.2 (App Router)                  │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Landing Page ─── Auth (JWT + OAuth2) ─── Role-Based Routing       │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │ │
│  │  │ AI Chat  │ │ Dashboard │ │ PDF Mgmt │ │ Voice    │ │ Email   │ │ │
│  │  │ (Role-   │ │ Analytics │ │ Kanban   │ │ Call UI  │ │Campaign │ │ │
│  │  │  based)  │ │ (12 wdgts)│ │ Board    │ │+Coaching │ │  UI     │ │ │
│  │  └──────────┘ └───────────┘ └──────────┘ └──────────┘ └─────────┘ │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │  ┌──────────────────┐  ┌────────────────┐  ┌────────────────────┐  │ │
│  │  │ Proposal Viewer  │  │  Onboarding    │  │  CRM Settings &   │  │ │
│  │  │ + Buyer Chat     │  │  Wizard        │  │  Sync Dashboard   │  │ │
│  │  │ (Public, No Auth)│  │  (5-step flow) │  │  (HubSpot OAuth)  │  │ │
│  │  └──────────────────┘  └────────────────┘  └────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  Tech: React 18 │ TypeScript │ Tailwind CSS │ shadcn/ui │ ApexCharts    │
│        Framer Motion │ Axios │ next-themes │ DOMPurify                   │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │ REST API + WebSocket
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    BACKEND — FastAPI (Python)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    MIDDLEWARE LAYER                                  │ │
│  │  CORS ── Session Mgmt ── JWT Auth (OAuth2 Bearer) ── Rate Limiting  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    API ROUTERS                                       │ │
│  │  ┌──────────────────────────────────────────────────────────────┐   │ │
│  │  │  /token, /register, /me          → Auth & User Management    │   │ │
│  │  │  /chat/response                  → AI Chat (RAG + LLM)      │   │ │
│  │  │  /admin/upload_pdf, /admin/ingest→ Document Management       │   │ │
│  │  │  /admin/generate_proposal        → Proposal Generation       │   │ │
│  │  │  /admin/call, /admin/get_summary → Voice Call Management     │   │ │
│  │  │  /admin/send_bulk_email          → Email Campaign            │   │ │
│  │  │  /admin/analytics               → Dashboard Analytics       │   │ │
│  │  │  /proposal/[id]                  → Public Proposal + Chat    │   │ │
│  │  │  /proposal/[id]/chat             → Buyer Chat (No Auth)      │   │ │
│  │  │  /webhook/vapi                   → Real-Time Call Coaching    │   │ │
│  │  │  /ws/coaching/[call_id]          → WebSocket Coaching Push    │   │ │
│  │  │  /crm/hubspot/*                 → CRM OAuth + Sync           │   │ │
│  │  └──────────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    CORE ENGINE MODULES                               │ │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │ │
│  │  │  ChatBot     │ │ PDFProcessor │ │ Coaching     │ │ HubSpot    │  │ │
│  │  │  Engine      │ │ + Vectorbase │ │ Engine       │ │ Sync       │  │ │
│  │  │  ─────────── │ │ ──────────── │ │ ──────────── │ │ ────────── │  │ │
│  │  │ ·Role-based  │ │ ·PDF Loading │ │ ·Objection   │ │ ·Contact   │  │ │
│  │  │  prompts     │ │ ·Text Split  │ │  Detection   │ │  Create    │  │ │
│  │  │ ·Memory Mgmt │ │ ·Cohere     │ │ ·Live Tips   │ │ ·Deal      │  │ │
│  │  │ ·Context     │ │  Embeddings │ │ ·Signal      │ │  Create    │  │ │
│  │  │  Injection   │ │ ·Multi-Query │ │  Analysis    │ │ ·Activity  │  │ │
│  │  │ ·Session     │ │  Retrieval  │ │ ·WebSocket   │ │  Logging   │  │ │
│  │  │  Tracking    │ │             │ │  Push        │ │ ·Auto Sync │  │ │
│  │  └─────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │ │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐                  │ │
│  │  │ BulkEmail   │ │ VAPICall     │ │ Proposal     │                  │ │
│  │  │ Sender      │ │ Manager      │ │ Generator    │                  │ │
│  │  │ ─────────── │ │ ──────────── │ │ ──────────── │                  │ │
│  │  │ ·SMTP       │ │ ·Twilio      │ │ ·LLM Summary │                  │ │
│  │  │ ·Template   │ │ ·Transcript  │ │ ·Markdown    │                  │ │
│  │  │ ·Batch Send │ │ ·Summary     │ │ ·HTML/PDF    │                  │ │
│  │  │ ·Tracking   │ │ ·Webhook     │ │ ·Engagement  │                  │ │
│  │  └─────────────┘ └──────────────┘ └──────────────┘                  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  Tech: FastAPI │ LangChain 0.1.13 │ Uvicorn │ bcrypt │ python-jose      │
│        pypandoc │ PyPDF │ APScheduler │ websockets                       │
└──────────┬─────────────┬──────────────┬──────────────┬───────────────────┘
           │             │              │              │
           ▼             ▼              ▼              ▼
┌────────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────────┐
│    MongoDB     │ │ Pinecone │ │ LLM APIs   │ │ External APIs    │
│    Atlas       │ │ Vector   │ │            │ │                  │
│ ────────────── │ │ Database │ │ ·Groq      │ │ ·VAPI (Voice)    │
│ ·chats         │ │ ──────── │ │  (llama-3.1│ │ ·Twilio (Phone)  │
│ ·proposals     │ │ ·Document│ │  -8b-instant)│ │ ·HubSpot CRM   │
│ ·endpoints     │ │  Chunks  │ │ ·OpenAI    │ │ ·SMTP (Email)    │
│ ·integrations  │ │ ·Cohere  │ │  (GPT-3.5) │ │ ·Cohere          │
│ ·sync_log      │ │  Embedds │ │ ·Fallback  │ │  (Embeddings)    │
│ ·onboarding    │ │ ·Cosine  │ │  Chain     │ │                  │
│ ·calls         │ │  Search  │ │            │ │                  │
└────────────────┘ └──────────┘ └────────────┘ └──────────────────┘
```

### Data Flow Architecture

```
┌─────────────────── CROSS-CHANNEL INTELLIGENCE LOOP ──────────────────┐
│                                                                       │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐   │
│   │  CHAT    │────▶│  CALLS   │────▶│ PROPOSALS│────▶│  EMAIL   │   │
│   │ Insights │     │ Insights │     │ Insights │     │ Insights │   │
│   └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘   │
│        │                │                │                │          │
│        │    Objections inform      Engagement data   Open rates      │
│        │    proposal content       triggers follow-  personalize     │
│        │                           up emails          chat tone      │
│        │                                                             │
│        └─────────────────────────────────────────────────────────────┘ │
│                     Every channel learns from every other              │
└───────────────────────────────────────────────────────────────────────┘
```

```
                    RAG PIPELINE (Chat Flow)

  User Query ──▶ Cohere Embedding ──▶ Pinecone Semantic Search
                                              │
                                     Top-5 Document Chunks
                                              │
                                              ▼
                                    Role-Based Prompt Template
                                    (USER / TEAM / ADMIN)
                                              │
                                              ▼
                                    Groq LLM (llama-3.1-8b-instant)
                                    ──────────────────
                                    Fallback: OpenAI GPT-3.5
                                              │
                                              ▼
                                    Response + Memory Update
                                    (MongoDB Session Storage)
```

```
              REAL-TIME SALES COACHING PIPELINE

  Live Call ──▶ VAPI Transcript Webhook ──▶ Coaching LLM Analysis
                                                    │
                                          Objection / Signal Detection
                                                    │
                                                    ▼
                                          WebSocket Push to Rep Screen
                                          ┌─────────────────────────┐
                                          │ 🔴 Budget Objection     │
                                          │ 💡 "Show ROI slide..."  │
                                          │ 📄 Ref: pricing.pdf p4  │
                                          └─────────────────────────┘
```

### Key Features:

- **AI-based role-aware responses** (tailored prompts for buyer, rep, and manager — not one-size-fits-all)
- **RAG-powered document intelligence** with multi-query retrieval and Pinecone vector search
- **Automatic proposal generation** from uploaded PDFs with LLM summarization → Markdown → HTML → PDF pipeline
- **Buyer-facing chat in proposals** — shareable link with embedded AI chat + lead capture (name/email)
- **Real-time sales coaching** — WebSocket-pushed objection detection and response tips during live calls
- **Cross-channel intelligence loop** — call insights improve proposals, chat data improves emails, email engagement personalizes AI tone
- **CRM auto-sync** (HubSpot) — zero double data entry; contacts, deals, activities sync automatically
- **30-minute onboarding** — 5-step guided wizard: company info → upload docs → train AI → test chat → share proposal

---

## 3. Technologies:

### Technology Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Next.js  │  │TypeScript│  │ Tailwind │  │ shadcn/  │            │
│  │ 16.2     │  │ + React  │  │   CSS    │  │ ui+Radix │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Apex     │  │ Framer   │  │  Axios   │  │ DOMPurify│            │
│  │ Charts   │  │ Motion   │  │ (HTTP)   │  │ (XSS)    │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ FastAPI  │  │ LangChain│  │ Uvicorn  │  │ PyPDF +  │            │
│  │ 0.110.2  │  │ 0.1.13   │  │ (ASGI)   │  │ pypandoc │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │python-   │  │ bcrypt / │  │WebSockets│  │APScheduler│            │
│  │jose(JWT) │  │ passlib  │  │ (coaching)│  │(bg jobs) │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     AI / ML / LLM LAYER                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   Groq   │  │  OpenAI  │  │  Cohere  │  │ Pinecone │            │
│  │ llama-3.1│  │ GPT-3.5  │  │Embeddings│  │ Vector   │            │
│  │ -8b-inst.│  │ (fallbck)│  │ (1024-d) │  │ Database │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     STORAGE & EXTERNAL                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ MongoDB  │  │  VAPI    │  │  Twilio  │  │ HubSpot  │            │
│  │ Atlas    │  │ (Voice   │  │ (Phone   │  │ CRM API  │            │
│  │ (NoSQL)  │  │  AI)     │  │  Routing)│  │ (OAuth2) │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Sources:
- **Company documents** (uploaded PDFs — product brochures, RFPs, contracts, datasheets)
- **Live call transcripts** (real-time via VAPI webhook)
- **Chat conversation history** (multi-turn sessions stored in MongoDB)
- **CRM contact & deal data** (bidirectional HubSpot sync)
- **Email engagement signals** (open/click tracking from SMTP)
- **Proposal engagement data** (view counts, buyer questions, time spent)

### Potential Impact on Target Audience:

**For Sales Reps:**
- Proposal generation reduced from **2–5 days → 30 minutes**
- Real-time coaching during calls eliminates guesswork on objection handling
- AI remembers context across sessions — no re-briefing needed

**For Sales Managers:**
- Analytics dashboard with 12+ widgets for pipeline visibility
- AI flags at-risk deals and surfaces team performance insights
- CRM auto-sync eliminates manual data entry, improving CRM adoption from ~40% → 95%

**For Buyers / End Customers:**
- Chat directly inside proposals — no need to schedule a call for simple questions
- Get instant, accurate, document-backed answers 24/7
- Frictionless experience builds trust and shortens decision time

### Benefits of the Solution:

- **Revenue Acceleration:** Faster deal cycles through AI-generated proposals and real-time coaching
- **Cost Reduction:** One platform replaces 4–5 separate tools (Gong + Outreach + DocSend + CRM + Email tool)
- **Data-Driven Selling:** Cross-channel intelligence loop means every interaction makes the next one smarter
- **Compliance Ready:** DOMPurify for XSS, JWT auth, role-based access, env-based secrets management
- **Scalability:** Stateless FastAPI + managed MongoDB Atlas + serverless Pinecone = horizontally scalable

---

## 4. Business Model & Unique Selling Proposition (USP):

### Business Model:

- **B2B SaaS Licensing:** Monthly/annual subscription per seat
- **Per-Seat Pricing:** Scales with team size, transparent tiers — no hidden credits
- **Tiered Plans:**
  - **Starter** ($49/user/month) — AI Chat, Proposals, Email Campaigns
  - **Growth** ($99/user/month) — + Voice Calls, CRM Sync, Real-Time Coaching
  - **Enterprise** (Custom) — + White-label, Dedicated Support, Compliance Tools, SSO
- **Volume Discounts:** 20%+ discount for 50+ seats (mid-market sweet spot)
- **Free Trial:** 14-day full-featured trial, no credit card required

### Unique Selling Proposition (USP):

1. **Interactive Proposals, Not Dead PDFs:**
   Not just generating a proposal — Pravaha creates a **shareable web link** where the buyer can read AND chat with AI about the proposal. The admin sees what the buyer asked and how long they spent on each section. No competitor does this.

2. **Real-Time Sales Coaching:**
   While your rep is on a live call, Pravaha **listens via transcript webhook**, detects objections in real-time, and **pushes coaching tips via WebSocket** to the rep's screen: "Buyer mentioned budget — show ROI slide." Only Outreach partially attempts this; Pravaha does it with open-source LLMs at a fraction of the cost.

3. **Cross-Channel Intelligence Loop:**
   Call transcripts inform proposal content. Buyer chat questions auto-improve proposal wording. Email click patterns personalize AI chat tone. **Every channel makes every other channel smarter.** No competitor connects insights across all channels.

4. **Zero-Complexity CRM Sync:**
   When a buyer opens a proposal → HubSpot Contact is created automatically. When a proposal is generated → HubSpot Deal is created. When a call ends → call summary is logged as a HubSpot Activity. **Zero double data entry.** Sales reps never touch the CRM manually.

5. **30-Minute Onboarding:**
   Upload 3 documents, train the AI, test it, share your first proposal — all in under 30 minutes. Salesforce Einstein takes 3 months of implementation. Outreach takes weeks. Pravaha takes a lunch break.

6. **Transparent Pricing:**
   Every major competitor (Outreach, Clari, Gong, Salesloft) hides pricing behind sales calls and credit systems. Pravaha publishes clear per-seat pricing on the website. No credits. No surprises. No "contact us for pricing."

7. **Role-Based AI Personas:**
   One platform, three completely different AI experiences — friendly product Q&A for buyers, objection-handling coach for reps, deal-health intelligence for managers. The AI adapts its tone, depth, and recommendations based on who is using it.

---

### Competitive Positioning:

| Capability | Pravaha | Gong | Outreach | Salesforce Einstein | HubSpot AI |
|---|:---:|:---:|:---:|:---:|:---:|
| AI Chat (RAG) | ✅ | ❌ | ❌ | ❌ | ✅ |
| Proposal Generation | ✅ | ❌ | ❌ | ❌ | ❌ |
| Buyer Chat in Proposals | ✅ | ❌ | ❌ | ❌ | ❌ |
| Real-Time Call Coaching | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| Voice Call Automation | ✅ | ✅ | ✅ | ❌ | ❌ |
| Bulk Email | ✅ | ❌ | ✅ | ✅ | ✅ |
| CRM Sync | ✅ | ✅ | ✅ | ✅ | ✅ |
| Cross-Channel Loop | ✅ | ❌ | ❌ | ❌ | ❌ |
| Transparent Pricing | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| <30 Min Onboarding | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| Mid-Market Affordable | ✅ | ❌ | ❌ | ❌ | ✅ |

**Target Customer:** Mid-market B2B SaaS companies (10–200 sales reps) who need more than Apollo but can't justify Gong/Clari pricing or Salesforce implementation timelines.

---

### Deployment:

| Component | Platform | URL |
|---|---|---|
| Frontend | Vercel | https://pravaha.vercel.app |
| Backend | Render | https://pravaha.onrender.com |
| Database | MongoDB Atlas | Cloud-managed |
| Vector DB | Pinecone | Cloud-managed |
| CRM | HubSpot | OAuth2 Integration |

---

*Team ARKA — Pravaha*
