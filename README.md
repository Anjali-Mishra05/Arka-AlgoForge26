<div align="center">

<!-- Hero Banner -->


# **PRAVAHA**

### *Flow in Sanskrit. Flow in Sales.*

[![Built at](https://img.shields.io/badge/Built%20at-AlgoForge%20'26-blueviolet?style=for-the-badge&logo=hackclub&logoColor=white)](https://github.com)
[![Status](https://img.shields.io/badge/Status-Live-brightgreen?style=for-the-badge&logo=statuspage&logoColor=white)](https://github.com)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge&logo=gnu&logoColor=white)](https://github.com)

<br/>

**AI-Powered Sales Automation Platform**
*One platform replacing 5 disconnected tools — Proposals, Calls, Coaching, Intelligence, Outreach*

<br/>

[Features](#-features) · [Tech Stack](#-tech-stack) · [Architecture](#-architecture) · [Getting Started](#-getting-started) · [Demo Flow](#-demo-flow) · [Team](#-team-arka)



</div>

---

## The Problem

```
Sales reps spend only 35% of their time actually selling.
The rest? CRM updates, writing proposals, preparing for calls.
                                                    — Salesforce Research
```

Today's sales teams juggle **5 disconnected tools** — CRM, call analysis, email automation, document editors, and proposal trackers. **None of them talk to each other.** The result?

| Pain Point | Real Impact |
|:---|:---|
| Manual proposal writing | **5–10 days** per proposal, ~₹10 lakh per deal |
| Post-call-only coaching | Reps freeze mid-call, deals die in real-time |
| Static PDF proposals | **22% open rate**, zero buyer intelligence |
| Fragmented dashboards | Managers stitch 5 reports to find one answer |

> **68% of sales reps miss quota every year** — not because they can't sell, but because their tools are broken.

---

## The Solution

**Pravaha** replaces the entire fragmented sales toolkit with **one AI-powered engine.**

```
Upload once → AI learns your catalogue → Sell everywhere → Know everything
```

---

## Features

<table>
<tr>
<td width="50%" valign="top">

### 1. Smart Onboarding
3-step setup. No coding. No IT team.
- Enter company details & industry
- Upload product catalogues (PDF)
- Hit **Train** — 14B parameter model learns everything via RAG

</td>
<td width="50%" valign="top">

### 2. PDF Vault & Kanban
Visual document management with drag-and-drop.
- Three-column Kanban: All Files → Selected → Proposals
- One-click ingestion into Pinecone vector DB
- One-click proposal generation from any document

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 3. Interactive Proposals ⭐ *USP*
**No competitor has this.**
- Generates **live HTML proposals** (not static PDFs)
- Built-in **AI chatbot** — buyers ask questions, get instant answers
- **No login/signup required** for buyers
- Full **Buyer Activity tracking** — views, time-on-page, questions asked
- Real-time notifications via **Zapier → Slack**

</td>
<td width="50%" valign="top">

### 4. AI Voice Agent
Automated client calls powered by AI.
- Deploys voice agent that **knows your entire catalogue**
- Live call status tracking (ID, duration, transcript)
- **Auto-generated call summary** — objections, buying signals, risk level
- One-click CRM note export to HubSpot

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 5. Sales Coach
Real-time, mid-call coaching.
- **8 objection templates** — Pricing, Competitor, Timing, Trust, Budget, Authority, Need, Urgency
- **RAG-powered** from your company's own playbook
- Instant counter-scripts during live conversations
- Context-aware — knows your products & differentiators

</td>
<td width="50%" valign="top">

### 6. Coaching Hub
Manager visibility into team performance.
- **Overview** — adoption rate, tips given, calls coached
- **Tip History** — full audit trail of every coaching moment
- **Leaderboard** — rep performance rankings
- **Playbook Editor** — customize objection templates

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 7. Mass Email
AI-personalized outreach at scale.
- Live preview before sending
- Template variables & personalization
- Delivery tracking & engagement metrics

</td>
<td width="50%" valign="top">

### 8. Unified Dashboard
One screen. Every insight. Every action.
- KPIs: Proposals, Views, Conversion Rate, Active Leads
- AI-powered **Next Best Action** with confidence scores
- **Daily Brief** — Top Risks, Opportunities, Rep Alerts
- Call Intelligence, Performance Analytics, Ops Queue

</td>
</tr>
</table>

---

## Tech Stack

<div align="center">

### Two Domains: **AI/ML** + **Full-Stack Web Development**

</div>

### Backend — AI & API Layer

| Component | Technology | Purpose |
|:---|:---|:---|
| **Framework** | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) | REST API + WebSocket server |
| **LLM** | ![Groq](https://img.shields.io/badge/Groq-F55036?style=flat-square&logo=lightning&logoColor=white) `llama-3.3-70b-versatile` | Chat, proposals, coaching, voice agent brain |
| **Embeddings** | ![Cohere](https://img.shields.io/badge/Cohere-39594D?style=flat-square&logo=cohere&logoColor=white) `embed-english-v3.0` | Document vectorization |
| **Vector DB** | ![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=flat-square&logo=pinecone&logoColor=white) | RAG retrieval — similarity search over catalogues |
| **Database** | ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white) Atlas | Users, proposals, sessions, coaching tips, analytics |
| **Voice** | ![VAPI](https://img.shields.io/badge/VAPI-5B21B6?style=flat-square&logo=twilio&logoColor=white) + Deepgram + Azure TTS | AI voice agent — calls, transcription, speech |
| **Auth** | ![JWT](https://img.shields.io/badge/JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white) + OAuth2 | Authentication & authorization |
| **Automation** | ![Zapier](https://img.shields.io/badge/Zapier-FF4A00?style=flat-square&logo=zapier&logoColor=white) | Webhooks for real-time notifications |

### Frontend — UI & Experience

| Component | Technology | Purpose |
|:---|:---|:---|
| **Framework** | ![Next.js](https://img.shields.io/badge/Next.js%2016-000000?style=flat-square&logo=nextdotjs&logoColor=white) | Full-stack React framework |
| **Language** | ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white) | Type-safe development |
| **Styling** | ![Tailwind](https://img.shields.io/badge/Tailwind%20CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white) | Utility-first CSS |
| **UI Components** | ![Radix](https://img.shields.io/badge/Radix%20UI-161618?style=flat-square&logo=radixui&logoColor=white) | Accessible component primitives |
| **Charts** | ![ApexCharts](https://img.shields.io/badge/ApexCharts-008FFB?style=flat-square&logo=chart.js&logoColor=white) | Dashboard analytics & visualizations |
| **Drag & Drop** | ![DnD Kit](https://img.shields.io/badge/DnD%20Kit-4F46E5?style=flat-square&logo=data:image/svg+xml;base64,&logoColor=white) + Hello Pangea | Kanban board & PDF vault |
| **Animations** | ![Framer](https://img.shields.io/badge/Framer%20Motion-0055FF?style=flat-square&logo=framer&logoColor=white) | Smooth transitions & micro-interactions |
| **Icons** | ![Lucide](https://img.shields.io/badge/Lucide-F56565?style=flat-square&logo=lucide&logoColor=white) | Consistent icon system |

### RAG Pipeline

```
PDF Upload
    │
    ▼
PyPDFLoader ──► RecursiveCharacterTextSplitter (1000 chars, 150 overlap)
                        │
                        ▼
                Cohere embed-english-v3.0
                        │
                        ▼
                Pinecone Upsert (batches of 96)
                        │
                        ▼
            Similarity Search on Query ──► Groq Llama 3.3 ──► Response
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    Next.js 16 + React 18                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Onboarding│ │Dashboard │ │Proposals │ │Sales Chat│           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
└───────┼─────────────┼───────────┼─────────────┼─────────────────┘
        │             │           │             │
        ▼             ▼           ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                                │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Auth     │ │ Chat     │ │ Admin    │ │ Events   │           │
│  │ Router   │ │ Router   │ │ Router   │ │ Router   │           │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
│       │             │           │             │                   │
│  ┌────▼─────────────▼───────────▼─────────────▼──────┐          │
│  │              UTILITY LAYER                         │          │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │          │
│  │  │Chatbot  │ │Coaching │ │Analytics│ │Call Mgr │ │          │
│  │  │Engine   │ │Engine   │ │Engine   │ │(VAPI)   │ │          │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ │          │
│  └───────────────────────────────────────────────────┘          │
└──────────┬──────────────┬──────────────┬────────────────────────┘
           │              │              │
     ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
     │  MongoDB  │ │ Pinecone  │ │   Groq    │
     │  Atlas    │ │ Vector DB │ │ Llama 3.3 │
     └───────────┘ └───────────┘ └───────────┘
```

---

## Project Structure

```
Pravaha/
│
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── seed.py                    # Database seeding
│   ├── requirements_fixed.txt     # Python dependencies
│   ├── routers/
│   │   ├── admin.py               # Admin endpoints
│   │   ├── chat.py                # Chat/coaching endpoints
│   │   └── events/                # Event-driven modules
│   │       ├── buyer_events.py    # Buyer activity tracking
│   │       ├── call_events.py     # Call management
│   │       ├── proposal_events.py # Proposal generation
│   │       └── email_events.py    # Email campaigns
│   ├── utils/
│   │   ├── auth.py                # JWT + OAuth2
│   │   ├── database.py            # MongoDB connection
│   │   ├── chatbot.py             # LLM chat engine
│   │   ├── coaching.py            # Sales coach logic
│   │   ├── call_handler.py        # VAPI integration
│   │   ├── analytics.py           # Dashboard analytics
│   │   ├── event_bus.py           # Real-time event system
│   │   ├── mcp_orchestrator.py    # MCP orchestration
│   │   └── zapier_webhooks.py     # Zapier automation
│   └── tests/                     # Test suite
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/            # Login, Register, OAuth
│   │   │   ├── onboarding/        # 5-step onboarding wizard
│   │   │   ├── dashboard/         # Main dashboard + sub-pages
│   │   │   │   ├── pdf/           # PDF Vault (Kanban)
│   │   │   │   ├── voice/         # AI Agent Calls
│   │   │   │   ├── proposals/     # Proposal management
│   │   │   │   ├── coaching/      # Coaching Hub (4 tabs)
│   │   │   │   └── email/         # Mass email campaigns
│   │   │   ├── proposal/[id]/     # Public buyer proposal room
│   │   │   ├── salesteam_chatbot/ # Sales Coach interface
│   │   │   └── chat/              # General chat
│   │   ├── components/            # Reusable UI components
│   │   └── lib/                   # Utilities & helpers
│   ├── public/images/             # Logos & feature images
│   ├── package.json
│   └── tailwind.config.ts
│
├── AGENTS.md                      # Architecture overview
├── ABSTRACT.md                    # System abstract
├── IMPLEMENTATION_PLAN.md         # Development roadmap
├── INDEX.md                       # Codebase reference
└── README.md                      # You are here
```

---

## Getting Started

### Prerequisites

```
Node.js >= 18    Python >= 3.10    MongoDB Atlas account
Pinecone account    Groq API key    VAPI account
```

### 1. Clone

```bash
git clone https://github.com/your-repo/pravaha.git
cd pravaha
```

### 2. Backend

```bash
cd Pravaha/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements_fixed.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
#   GROQ_API_KEY, PINECONE_API_KEY, COHERE_API_KEY,
#   MONGODB_URI, VAPI_API_KEY, JWT_SECRET

# Seed database (optional)
python seed.py

# Start server
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd Pravaha/frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with backend URL

# Start dev server
npm run dev
```

### 4. Open

```
Frontend  →  http://localhost:3000
Backend   →  http://localhost:8000
API Docs  →  http://localhost:8000/docs
```

---

## Demo Flow

> *The recommended order for presenting Pravaha's features:*

```
START
  │
  ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. ONBOARDING  │────►│  2. PDF VAULT   │────►│  3. GENERATE    │
│  Company setup  │     │  Kanban board   │     │  Proposal       │
│  + PDF upload   │     │  Drag & drop    │     │  (background)   │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┘
                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  4. AI VOICE    │────►│  5. INTERACTIVE │────►│  6. BUYER       │
│  AGENT CALL     │     │  PROPOSAL +     │     │  ACTIVITY       │
│  + Live summary │     │  AI CHATBOT     │     │  + Notifications│
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌────────────────────────────────┘
                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  7. SALES COACH │────►│  8. COACHING    │────►│  9. MASS EMAIL  │
│  Mid-call RAG   │     │  HUB (4 tabs)  │     │  + Live preview │
│  8 templates    │     │  Leaderboard   │     │                 │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
                                                ┌─────────────────┐
                                                │  10. DASHBOARD  │
                                                │  Everything in  │
                                                │  one screen     │
                                                └─────────────────┘
                                                         │
                                                         ▼
                                                       DONE
```

---

## Competitive Advantage

<div align="center">

| Capability | Salesforce | Gong | Proposify | HubSpot | **Pravaha** |
|:---|:---:|:---:|:---:|:---:|:---:|
| AI Proposal Generation | - | - | Static PDF | - | **Interactive HTML + Chatbot** |
| Buyer Activity Tracking | - | - | Open rate only | Basic | **Questions, time, engagement score** |
| Voice Agent Calls | - | Post-call | - | - | **Real-time AI agent** |
| Mid-Call Coaching | - | - | - | - | **RAG from your playbook** |
| Unified Dashboard | Partial | - | - | Partial | **Everything, one screen** |
| Setup Time | Weeks | Days | Hours | Days | **2 minutes** |
| Cost (Annual) | ~₹60-80L | ~₹1Cr+ | ~₹50K | ~₹40L | **₹3L** |

</div>

---

## Documentation

| Document | Description |
|:---|:---|
| [`AGENTS.md`](./Pravaha/AGENTS.md) | Architecture & team overview |
| [`ABSTRACT.md`](./Pravaha/ABSTRACT.md) | System architecture abstract |
| [`IMPLEMENTATION_PLAN.md`](./Pravaha/IMPLEMENTATION_PLAN.md) | Development roadmap |
| [`INDEX.md`](./Pravaha/INDEX.md) | Complete codebase reference |
| [`architecture.md`](./Pravaha/architecture.md) | Technical architecture details |

---

## Team Arka

<div align="center">

**Built with sleep deprivation and passion at AlgoForge '26**

*Pravaha — kyunki sales mein flow rukna nahi chahiye.*

</div>

---

<div align="center">

**Domains:** `AI / Machine Learning` · `Full-Stack Web Development`

<br/>

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)

<br/>

<sub>Built at AlgoForge '26 Hackathon | License: Proprietary</sub>

</div>
