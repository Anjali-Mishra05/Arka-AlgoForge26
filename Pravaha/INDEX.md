# Pravaha - AI-Powered Sales Assistant | Complete Codebase Index

> **Status note**: This file is not authoritative. The live version is at the repo root: [`INDEX.md`](../INDEX.md).



---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Directory Structure](#directory-structure)
5. [Backend Guide](#backend-guide)
6. [Frontend Guide](#frontend-guide)
7. [Database & Storage](#database--storage)
8. [API Endpoints](#api-endpoints)
9. [Configuration & Environment](#configuration--environment)
10. [Key Features](#key-features)
11. [Deployment](#deployment)
12. [File Reference](#file-reference)

---

## Project Overview

Pravaha is an AI-powered sales automation platform that helps teams:
- Conduct intelligent conversations with AI-driven sales assistant
- Upload and analyze PDF documents for context
- Generate automated sales proposals
- Execute voice-based calls with prospects
- Send bulk email campaigns
- Track analytics and sales metrics

**Core Functionality**:
- Multi-turn conversational AI with memory
- Document-based context awareness (RAG - Retrieval Augmented Generation)
- Intelligent proposal generation from documents
- Voice call automation with Twilio & VAPI
- Dashboard with real-time analytics

---

## Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                       │
│  - Login/Auth → Chat Interface → Dashboard → Admin Tools   │
│  - Port: 3000 | Framework: Next.js 16.2                    │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API (Axios)
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                        │
│  /admin/ → PDF Upload, Proposal Generation, Email, Calls   │
│  /chat/  → Conversational AI Responses                      │
│  /token/ → Authentication & Authorization                   │
│  Port: 8000 | Framework: FastAPI 0.110.2                   │
└──────┬──────────────────────────┬──────────────────────────┘
       │                          │
       ↓                          ↓
┌──────────────┐      ┌──────────────────────┐
│  MongoDB     │      │  Pinecone            │
│  - chats     │      │  - Document embeddings
│  - endpoints │      │  - Semantic search   │
│  - proposal  │      │  - Vector storage    │
└──────────────┘      └──────────────────────┘
       ↑                          ↑
       └──────────────┬───────────┘
            External Services
            - Groq (LLM: llama-3.1-8b-instant)
            - OpenAI (GPT-3.5-turbo)
            - Cohere (Embeddings)
            - VAPI (Voice Calls)
            - Twilio (Phone)
            - SMTP (Email)
```

### Data Flow

**Chat Flow**:
```
User Message → Frontend → Backend Chat Router →
  LangChain ChatBot → Pinecone Vector Search →
  Document Context Retrieval → LLM Generation →
  Response with Memory Update → Frontend Display
```

**PDF Processing Flow**:
```
PDF Upload → Store in all_documents/ →
  Select for Processing → LangChain PDF Loader →
  Text Splitting → Cohere Embeddings →
  Pinecone Index → Ready for Chat Context
```

**Proposal Generation Flow**:
```
Selected PDFs → LangChain Summarization →
  LLM Template Generation → Markdown Output →
  Pandoc HTML Conversion → HTML to PDF →
  Store in all_documents/
```

---

## Technology Stack

### Backend
| Component | Technology | Version |
|-----------|------------|---------|
| **Framework** | FastAPI | 0.110.2 |
| **Server** | Uvicorn | Latest |
| **Language** | Python | 3.9+ |
| **LLM Orchestration** | LangChain | 0.1.13 |
| **Primary LLM** | Groq (llama-3.1-8b-instant) | - |
| **Fallback LLM** | OpenAI GPT-3.5-turbo | - |
| **Embeddings** | Cohere | - |
| **Vector DB** | Pinecone | 3.2.2 |
| **Primary DB** | MongoDB | (PyMongo 4.7.0) |
| **Auth** | JWT + OAuth2 | python-jose |
| **Password Hashing** | bcrypt | Latest |
| **PDF Processing** | PyPDF | 4.2.0 |
| **PDF Conversion** | pypandoc | Latest |
| **Audio Processing** | librosa, soundfile | Latest |
| **Voice Integration** | VAPI + Twilio | - |
| **Email** | Python SMTP | Built-in |

### Frontend
| Component | Technology | Version |
|-----------|------------|---------|
| **Framework** | Next.js | 16.2 |
| **Language** | TypeScript/TSX | Latest |
| **Styling** | Tailwind CSS | Latest |
| **UI Components** | shadcn/ui (Radix) | Latest |
| **Charts** | ApexCharts | Latest |
| **HTTP Client** | Axios | Latest |
| **Animations** | Framer Motion | Latest |
| **Theme** | next-themes | Latest |
| **Markdown** | react-markdown | Latest |
| **Drag & Drop** | @dnd-kit | Latest |
| **Toast Notifications** | react-hot-toast | Latest |
| **Icons** | lucide-react | Latest |

---

## Directory Structure

### Full Tree View

```
Pravaha/
│
├── backend/                              # Python FastAPI Backend
│   ├── main.py                          # FastAPI application entry point
│   ├── userbot.py                       # Alternative chatbot implementation
│   ├── requirements_fixed.txt           # Python dependencies
│   ├── .env.example                     # Environment variables template
│   ├── Procfile                         # Deployment configuration (Render/Heroku)
│   │
│   ├── routers/                         # API route handlers
│   │   ├── admin/                       # Admin-only operations
│   │   │   ├── __init__.py
│   │   │   ├── upload.py               # PDF upload and document management
│   │   │   ├── generate_proposal.py    # Proposal generation engine
│   │   │   └── analytics.py            # Analytics aggregation
│   │   │
│   │   └── chat/                        # Chat-related endpoints
│   │       ├── __init__.py
│   │       └── response.py              # Chat message handling
│   │
│   ├── utils/                           # Utility modules
│   │   ├── __init__.py
│   │   ├── chatbot.py                  # LangChain ChatBot class with memory
│   │   ├── database.py                 # MongoDB operations
│   │   ├── vectorbase.py               # Pinecone vector database operations
│   │   ├── auth.py                     # JWT & OAuth2 authentication
│   │   ├── call.py                     # VAPI voice call integration
│   │   ├── bulkEmailSend.py            # SMTP bulk email sender
│   │   ├── requirements.txt            # Utility-specific dependencies
│   │   └── [other utility files]
│   │
│   ├── all_documents/                   # Storage for uploaded & generated files
│   │   ├── proposal.md                 # Generated proposal (markdown)
│   │   ├── proposal.html               # Generated proposal (HTML)
│   │   ├── proposal.pdf                # Generated proposal (PDF)
│   │   ├── [uploaded PDFs]
│   │   └── [other documents]
│   │
│   └── input_documents/                 # Selected documents for processing
│       └── [PDFs selected for ingestion]
│
├── frontend/                            # Next.js React Frontend (TypeScript)
│   ├── package.json                    # Node.js dependencies & scripts
│   ├── package-lock.json               # Locked dependency versions
│   ├── tsconfig.json                   # TypeScript configuration
│   ├── next.config.mjs                 # Next.js configuration
│   ├── tailwind.config.ts              # Tailwind CSS configuration
│   ├── .eslintrc.json                  # ESLint rules
│   ├── components.json                 # shadcn/ui component registry
│   ├── README.md                       # Frontend setup guide
│   │
│   ├── public/                          # Static assets (images, icons)
│   │   ├── favicon.ico
│   │   └── [images, logos, etc]
│   │
│   └── src/                            # Source code
│       ├── app/                        # Next.js App Router (pages)
│       │   ├── page.tsx                # Landing page (/)
│       │   ├── layout.tsx              # Root layout
│       │   ├── globals.css             # Global styles
│       │   │
│       │   ├── (auth)/                 # Authentication routes
│       │   │   ├── login/
│       │   │   │   └── page.tsx        # Login page
│       │   │   └── signup/
│       │   │       └── page.tsx        # Signup page
│       │   │
│       │   ├── chat/                   # Chat interface
│       │   │   └── page.tsx            # Chat page with AI assistant
│       │   │
│       │   ├── dashboard/              # Admin dashboard
│       │   │   ├── layout.tsx          # Dashboard layout wrapper
│       │   │   ├── page.tsx            # Main dashboard with analytics
│       │   │   ├── email/
│       │   │   │   └── page.tsx        # Email campaign interface
│       │   │   ├── pdf/
│       │   │   │   └── page.tsx        # PDF upload/management
│       │   │   └── voice/
│       │   │       └── page.tsx        # Voice call interface
│       │   │
│       │   └── salesteam_chatbot/      # Sales team interface
│       │       └── page.tsx            # Dedicated chatbot for sales team
│       │
│       ├── components/                 # Reusable React components
│       │   ├── analytics/              # Dashboard analytics widgets (12 files)
│       │   │   ├── analytics.tsx       # Main analytics container
│       │   │   ├── visitor.tsx         # Visitor statistics
│       │   │   ├── average-positions.tsx
│       │   │   ├── completed-goals.tsx
│       │   │   ├── completed-rates.tsx
│       │   │   ├── deal-status.tsx
│       │   │   ├── recent-leads.tsx
│       │   │   ├── sales-country.tsx
│       │   │   ├── session-browser.tsx
│       │   │   ├── top-performing.tsx
│       │   │   ├── top-queries.tsx
│       │   │   └── to-do-list.tsx
│       │   │
│       │   ├── charts/                 # Chart components (11 variations)
│       │   │   ├── AreaChart.tsx
│       │   │   ├── AreaChartWithActions.tsx
│       │   │   ├── BarChart.tsx
│       │   │   ├── BarChartBackground.tsx
│       │   │   ├── BarChartActionless.tsx
│       │   │   ├── DonutChart.tsx
│       │   │   ├── LineChart.tsx
│       │   │   ├── PieChart.tsx
│       │   │   ├── RadialBarChart.tsx
│       │   │   └── [other variants]
│       │   │
│       │   ├── ui/                    # shadcn/ui components
│       │   │   ├── avatar.tsx
│       │   │   ├── button.tsx
│       │   │   ├── card.tsx
│       │   │   ├── checkbox.tsx
│       │   │   ├── dropdown-menu.tsx
│       │   │   ├── input.tsx
│       │   │   ├── label.tsx
│       │   │   ├── progress.tsx
│       │   │   ├── scroll-area.tsx
│       │   │   ├── skeleton.tsx
│       │   │   ├── switch.tsx
│       │   │   ├── table.tsx
│       │   │   └── textarea.tsx
│       │   │
│       │   ├── Spotlight.tsx           # Custom spotlight animation
│       │   ├── vortex.tsx              # Custom vortex animation
│       │   ├── ChatbotResponse.tsx     # AI response display
│       │   ├── PromptBox.tsx           # Input prompt interface
│       │   ├── Sidebar.tsx             # Navigation sidebar
│       │   ├── ColumnContainer.tsx     # Layout container
│       │   ├── TaskCard.tsx            # Task card component
│       │   ├── UserChat.tsx            # User chat component
│       │   ├── chat.tsx                # Chat message display
│       │   ├── theme-provider.tsx      # Dark/light theme provider
│       │   ├── theme-based-image.tsx   # Responsive image based on theme
│       │   │
│       │   ├── landing/                # Landing page components
│       │   │   ├── header.tsx
│       │   │   ├── footer.tsx
│       │   │   ├── landing-navbar.tsx
│       │   │   ├── demos.tsx
│       │   │   └── pricing.tsx
│       │   │
│       │   └── icons/                  # Custom SVG icons
│       │       ├── twitter.tsx
│       │       ├── linkedin.tsx
│       │       ├── chrome.tsx
│       │       └── [other icons]
│       │
│       ├── lib/                        # Utility functions
│       │   ├── base-chart-options.ts  # ApexCharts default configs
│       │   ├── currency.ts            # Currency formatting
│       │   ├── events.ts              # Event handling
│       │   └── utils.ts               # General helpers
│       │
│       └── __fakeData__/              # Mock data for development
│           ├── countries.ts           # Country list
│           └── map/
│               └── worldMap.json      # World map GeoJSON
│
└── resources/                          # Documentation & screenshots
    └── [screenshots, docs, guides]
```

---

## Backend Guide

### Main Entry Point: `/backend/main.py`

**Key Features**:
- CORS enabled for: localhost:3000, Vercel deploy, production URLs
- Session middleware for request tracking
- OpenAPI documentation at `/docs`
- JWT authentication with OAuth2 bearer tokens
- Mock user database with 3 roles: USER, ADMIN, TEAM

**Registered Routers**:
```python
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
```

### Core Modules

#### 1. **`utils/chatbot.py`** - AI Conversation Engine
```
Class: ChatBot
├── __init__(mongodb_connection, pinecone_index)
├── create_chain(context) → LangChain Conversation Chain
├── get_response(user_input, session_id) → str
├── update_memory(session_id, user, assistant) → None
└── close_session(session_id) → None

Features:
- Uses Groq `llama-3.1-8b-instant` as the primary chat LLM
- Memory: Conversation buffer from MongoDB
- Prompt Template: Sales assistant role with context injection
- Multi-turn context awareness
- Document retrieval via Pinecone
```

**LLM Fallback Chain**:
1. **Groq llama-3.1-8b-instant** (primary, fast, low-cost)
2. **OpenAI GPT-3.5-turbo** (fallback, paid)

#### 2. **`utils/database.py`** - MongoDB Operations
```
Collections:
├── chats
│   └── Structure: {
│       "session_id": string,
│       "user_id": string,
│       "created_at": datetime,
│       "sessions": [{
│           "user": string,
│           "message": string,
│           "timestamp": datetime
│       }]
│   }
├── endpoints
│   └── API usage tracking with counters
└── proposal
    └── Generated proposal metadata
```

#### 3. **`utils/vectorbase.py`** - RAG & Vector Search
```
Class: PDFProcessor
├── load_pdf(file_path) → Document[]
├── split_documents(docs, chunk_size=1000) → Chunks[]
├── create_embeddings(chunks) → Cohere embeddings
├── ingest_to_pinecone(embeddings, index_name) → None
└── retrieve_context(query, top_k=5) → Context[]

Retriever: MultiQueryRetriever
- Generates multiple query variations
- Semantic search across document chunks
- Returns top-k relevant contexts
```

#### 4. **`utils/auth.py`** - Authentication & Authorization
```
Mock Users:
├── "user" (password: "user123") - USER role
├── "admin" (password: "admin123") - ADMIN role
└── "team" (password: "team123") - TEAM role

Functions:
├── create_access_token(data, expires_delta) → JWT token
├── verify_token(token) → Payload
├── get_current_user(token) → User
├── hash_password(password) → bcrypt hash
└── verify_password(plain, hashed) → bool

Token Structure:
{
  "sub": "username",
  "exp": timestamp,
  "role": "USER|ADMIN|TEAM"
}
```

#### 5. **`utils/call.py`** - Voice Call Integration
```
Class: VAPICallManager
├── initiate_call(phone_number, context) → call_id
├── get_call_status(call_id) → status
├── get_call_summary(call_id) → summary
└── end_call(call_id) → None

Integration:
- VAPI API for voice conversations
- Twilio for phone routing
- Call summaries extracted from VAPI responses
```

#### 6. **`utils/bulkEmailSend.py`** - Email Campaigns
```
Class: BulkEmailSender
├── __init__(smtp_server, port, username, password)
├── send_bulk_email(recipients, subject, body, template) → results
├── personalize_template(template, user_data) → personalized_body
└── validate_emails(recipient_list) → valid_list

Configuration:
- SMTP server (configurable)
- TLS/SSL encryption
- HTML email support
- Template substitution variables
```

#### 7. **`routers/admin/upload.py`** - Document Management
```
POST /admin/upload_pdf
├── Accepts: PDF files (multipart/form-data)
├── Validation: File type, size limits
├── Storage: ./all_documents/{filename}
└── Response: {filename, size, status}

POST /admin/update_selected_docs
├── Accepts: {documents: [filename, ...]}
├── Action: Copy to ./input_documents/ for processing
└── Response: {selected_count, copied_files}
```

#### 8. **`routers/admin/generate_proposal.py`** - Proposal Engine
```
POST /admin/generate_proposal
├── Input: Selected documents from input_documents/
├── Process:
│   1. Load all PDFs
│   2. Summarize using LangChain Summarization Chain
│   3. Generate markdown via LLM
│   4. Convert markdown → HTML (pypandoc)
│   5. Convert HTML → PDF (pypdf)
├── Output:
│   - proposal.md (Markdown)
│   - proposal.html (HTML)
│   - proposal.pdf (PDF)
└── Storage: ./all_documents/

Functions:
├── summarize_documents(pdf_paths) → summary_text
├── generate_proposal_text(summary) → markdown
├── convert_to_html(markdown) → html
└── convert_to_pdf(html) → pdf_bytes
```

#### 9. **`routers/chat/response.py`** - Chat Handler
```
POST /chat/response
├── Body: {
│   "user_input": string,
│   "session_id": string,
│   "context": string (optional)
│ }
├── Process:
│   1. Retrieve documents from Pinecone
│   2. Inject context into prompt
│   3. Call ChatBot.get_response()
│   4. Update session memory
└── Response: {
    "response": string,
    "session_id": string,
    "context_used": [documents],
    "timestamp": datetime
  }

Features:
- Multi-turn conversation
- Context awareness
- Document retrieval injection
- Session tracking
```

---

## Frontend Guide

### Page Architecture

#### **Landing Page** (`/page.tsx`)
```
Components:
├── LandingNavbar - Navigation with theme toggle
├── Hero Section - Spotlight effect background
│   └── CTA buttons: Login/Signup
├── Demos Section - Feature showcase
├── Pricing Section - Pricing table
└── Footer

Features:
- Responsive design
- Dark mode support
- Call-to-action optimization
```

#### **Authentication Pages**
```
/login (/auth/login/page.tsx)
├── Email/Username input
├── Password input
├── "Forgot Password" link
├── "Sign up" redirect
└── POST to backend /token endpoint

/signup (/auth/signup/page.tsx)
├── Name input
├── Email input
├── Password input (with strength indicator)
├── Confirm password
└── POST to backend /register endpoint
```

#### **Chat Interface** (`/chat/page.tsx`)
```
Structure:
├── Header (with theme toggle)
├── Chat Display Area
│   ├── User Messages
│   ├── Bot Messages (ChatbotResponse component)
│   └── Audio playback toggle
└── Input Area (PromptBox component)
   └── Send button

Features:
- Real-time message display
- Text-to-speech for bot responses
- Message history
- Session management
- Auto-scroll to latest message
- Markdown rendering support
- Code block highlighting

Integration:
- Calls POST /chat/response
- Stores session_id in localStorage
- Maintains conversation context
```

#### **Dashboard** (`/dashboard/page.tsx`)
```
Layout:
├── Sidebar Navigation
│   ├── Dashboard (home)
│   ├── Email
│   ├── PDF Upload
│   └── Voice Calls
└── Main Content Area
   ├── Analytics Widgets (12 components)
   ├── Proposal Generation Button
   └── Data refresh controls

Analytics Widgets:
├── Visitor Statistics
├── Sales by Country
├── Deal Status
├── Recent Leads
├── Top Performing Products
├── Completion Rates
├── Browser Sessions
├── Top Queries
├── Task/To-Do List
├── Goal Completion
├── Average Positions
└── Custom metrics

Data Source:
- GET /admin/analytics

Theme:
- Dark/Light mode toggle
- Persistent theme selection
```

##### **Dashboard Sub-pages**

**Email Interface** (`/dashboard/email/page.tsx`)
```
Features:
- Recipient list input
- Email template editor
- Subject line
- Preview panel
- Send button
- Bulk email submission to /admin/send_bulk_email
```

**PDF Management** (`/dashboard/pdf/page.tsx`)
```
Features:
- File upload interface (drag & drop)
- Uploaded documents list
- Document selection checkboxes
- "Process Selected" button
- Document preview
- Delete document option
```

**Voice Calls** (`/dashboard/voice/page.tsx`)
```
Features:
- Phone number input
- Call script/template
- Initiate call button
- Call history
- Call status tracking
- Summary display
- Recording availability
```

#### **Sales Team Chatbot** (`/salesteam_chatbot/page.tsx`)
```
Features:
- Dedicated chat interface
- Role-based context injection
- Sales-specific templates
- Team access control
```

### Component System

#### **Analytics Components** (12 widgets)
All located in `/src/components/analytics/`

```
visitor.tsx           → Visitor count & trend
average-positions.tsx → Average ranking positions
completed-goals.tsx   → Goals completion metric
completed-rates.tsx   → Success rate display
deal-status.tsx       → Deal pipeline status
recent-leads.tsx      → Latest leads table
sales-country.tsx     → Geographic sales map
session-browser.tsx   → Browser usage stats
top-performing.tsx    → Top products/regions
top-queries.tsx       → Popular search queries
to-do-list.tsx        → Task management
analytics.tsx         → Main container & layout

Each uses:
- ApexCharts for data visualization
- Real data from API or mock data
- Responsive grid layout
- Dark mode support
```

#### **Chart Components** (11 variations)
All use ApexCharts with custom styling:

```
AreaChart.tsx              → Standard area chart
AreaChartWithActions.tsx   → Area + action buttons
BarChart.tsx               → Standard bar chart
BarChartBackground.tsx     → Bar with background gradient
BarChartActionless.tsx     → Simplified bar chart
DonutChart.tsx             → Donut/ring chart
LineChart.tsx              → Line chart with markers
PieChart.tsx               → Pie chart breakdown
RadialBarChart.tsx         → Radial/circular bar
[other variants]           → Specific use cases

Base Configuration:
- Handled by: lib/base-chart-options.ts
- Customizations:
  - Color schemes (light/dark mode)
  - Font family (Geist Sans)
  - Responsive sizing
  - Legend positioning
  - Tooltip formatting
```

#### **UI Components** (shadcn/ui)
Located in `/src/components/ui/`

```
Primitive Components:
├── button.tsx        - Button with variants
├── input.tsx         - Text input field
├── textarea.tsx      - Multi-line text
├── label.tsx         - Form label
├── checkbox.tsx      - Checkbox input
├── avatar.tsx        - User avatar display
├── card.tsx          - Card container
├── dropdown-menu.tsx - Dropdown navigation
├── progress.tsx      - Progress bar
├── scroll-area.tsx   - Scrollable container
├── skeleton.tsx      - Loading skeleton
├── switch.tsx        - Toggle switch
└── table.tsx         - Data table

Each component:
- Built on Radix UI primitives
- Fully accessible (ARIA)
- Styled with Tailwind CSS
- Dark mode compatible
- TypeScript typed
```

#### **Custom Components**
```
Spotlight.tsx
├── Custom hook: useMousePosition()
├── Spotlight effect on mouse movement
├── Used for landing page hero
└── Animated background gradient

vortex.tsx
├── SVG-based vortex animation
├── Background effect
├── Performance optimized

ChatbotResponse.tsx
├── Renders AI responses
├── Markdown support
├── Code syntax highlighting
├── Links and formatting
├── Audio playback integration

PromptBox.tsx
├── User input area
├── Send button
├── File attachment support
├── Character counter (optional)

Sidebar.tsx
├── Navigation menu
├── Active page highlighting
├── Role-based menu items
├── Collapsible on mobile

ColumnContainer.tsx
├── Grid/flex layout wrapper
├── Responsive column management
├── Spacing normalization

TaskCard.tsx
├── Individual task display
├── Status badges
├── Due date display
├── Quick actions (edit, delete, complete)

UserChat.tsx
├── User message bubble
├── Timestamp display
├── Message status (sent, delivered)

theme-provider.tsx
├── Theme context wrapper
├── Dark/light mode toggle
├── Persists to localStorage

theme-based-image.tsx
├── Conditional image rendering
├── Light mode image
├── Dark mode image
```

### Styling & Theme System

**Tailwind CSS** (`tailwind.config.ts`)
```typescript
Configuration:
├── Color scheme (light/dark)
├── Custom colors
├── Animation definitions
├── Font configuration (Geist Sans, Geist Mono)
├── Border radius
├── Shadow definitions
└── Dark mode: class-based

Custom Animations:
├── Spotlight effect
├── Pulse effects
├── Slide animations
├── Fade-in/out
└── Vortex animation
```

**Dark Mode**
- Provider: `next-themes`
- Trigger: Theme toggle button
- Storage: localStorage
- System preference fallback

### Utility Functions

**`lib/base-chart-options.ts`**
```
Exports:
├── getAreaChartOptions() → ApexCharts config
├── getBarChartOptions() → ApexCharts config
├── getLineChartOptions() → ApexCharts config
├── customizeChartForTheme(theme) → config adjustments
└── [chart-specific configs]
```

**`lib/currency.ts`**
```
Exports:
├── formatCurrency(amount, currency) → "€1,234.56"
├── parseCurrency(string) → number
└── getCurrencySymbol(code) → symbol
```

**`lib/events.ts`**
```
Exports:
├── debounce(fn, delay) → debounced function
├── throttle(fn, delay) → throttled function
└── [event handling utilities]
```

**`lib/utils.ts`**
```
Exports:
├── cn(...classes) → merged class string
├── clsx() → conditional class builder
└── [general utilities]
```

---

## Database & Storage

### MongoDB Collections

#### **chats Collection**
```javascript
Document Structure:
{
  "_id": ObjectId,
  "session_id": "uuid-string",
  "user_id": "username",
  "created_at": ISODate("2026-03-17T10:00:00Z"),
  "updated_at": ISODate("2026-03-17T10:30:00Z"),
  "sessions": [
    {
      "user": "user_message_content",
      "message": "user input text",
      "timestamp": ISODate("2026-03-17T10:00:05Z"),
      "role": "human"
    },
    {
      "user": "assistant_response_content",
      "message": "ai generated response",
      "timestamp": ISODate("2026-03-17T10:00:06Z"),
      "role": "assistant"
    }
  ],
  "metadata": {
    "document_context": ["doc1.pdf", "doc2.pdf"],
    "model_used": "llama-3.1-8b-instant",
    "tokens_used": 1543
  }
}

Indexes:
- session_id (unique)
- user_id
- created_at (TTL: 30 days)
```

#### **endpoints Collection**
```javascript
Document Structure:
{
  "_id": ObjectId,
  "endpoint_name": "/chat/response",
  "user_id": "username",
  "call_count": 245,
  "last_called": ISODate("2026-03-17T10:30:00Z"),
  "average_response_time_ms": 342,
  "error_count": 2
}

Tracks:
- API endpoint usage
- Rate limiting data
- Performance metrics
- Error tracking
```

#### **proposal Collection**
```javascript
Document Structure:
{
  "_id": ObjectId,
  "proposal_id": "uuid",
  "user_id": "admin_username",
  "created_at": ISODate("2026-03-17T10:00:00Z"),
  "documents_used": ["doc1.pdf", "doc2.pdf"],
  "content": {
    "markdown": "# Proposal\n...",
    "html": "<html>...",
    "pdf_url": "/all_documents/proposal.pdf"
  },
  "metadata": {
    "summary": "Brief proposal summary",
    "total_pages": 5,
    "estimated_value": "$50,000"
  }
}

Indexes:
- proposal_id (unique)
- user_id
- created_at
```

### File Storage

#### **`/backend/all_documents/`**
```
Purpose: Central storage for all documents
Contains:
├── [uploaded PDFs]
│   ├── document_1.pdf
│   ├── document_2.pdf
│   └── ...
├── proposal.md        # Generated proposal (markdown)
├── proposal.html      # Generated proposal (HTML)
├── proposal.pdf       # Generated proposal (PDF)
└── [other generated files]

Access:
- GET /admin/get_html_from_file?file=proposal.html
- Web server serves files statically
```

#### **`/backend/input_documents/`**
```
Purpose: Staging area for documents to be processed
Contains:
├── [selected PDFs from all_documents/]
├── Being processed by:
│   - PDF loader (LangChain)
│   - Text splitter
│   - Embedding generator
│   └── Pinecone indexer

Lifecycle:
1. Upload to all_documents/
2. User selects via /admin/update_selected_docs
3. Copy to input_documents/
4. Process (ingest) to Pinecone
5. Ready for RAG queries
```

### Pinecone Vector Database

```
Index Configuration:
├── Index Name: [from environment INDEX_NAME]
├── Dimension: 1024 (Cohere embeddings)
├── Metric: cosine similarity
├── Storage: Managed by Pinecone

Vector Namespace: default

Document Chunks:
├── Each chunk: ~1000 characters
├── Embedding: Generated via Cohere
├── Metadata: {
│   "source": "document_name.pdf",
│   "chunk_index": 0,
│   "content_preview": "First 100 chars...",
│   "created_at": timestamp
│ }

Query Process:
1. User query → Cohere embedding
2. Semantic search → top-5 matches
3. MultiQueryRetriever generates variations
4. Retrieve context for LLM injection
5. Context → ChatBot for response generation
```

---

## API Endpoints

### Authentication Endpoints

#### `GET/POST /token`
```
Purpose: Get authentication token
Method: POST (OAuth2)
Auth: Basic (username:password)
Response: {
  "access_token": "jwt_token",
  "token_type": "bearer",
  "expires_in": 3600
}

Mock Credentials:
- user / user123 → USER role
- admin / admin123 → ADMIN role
- team / team123 → TEAM role
```

#### `POST /register`
```
Purpose: Register new user
Body: {
  "username": string,
  "password": string,
  "email": string
}
Response: {
  "user_id": string,
  "username": string,
  "message": "User registered successfully"
}
```

#### `GET /me`
```
Purpose: Get current user info
Auth: Bearer token required
Response: {
  "user_id": string,
  "username": string,
  "role": "USER|ADMIN|TEAM",
  "created_at": datetime
}
```

#### `GET /secure-route`
```
Purpose: Test protected route
Auth: Bearer token required
Response: {
  "message": "This is a protected route"
}
```

### Chat Endpoints

#### `POST /chat/response`
```
Purpose: Get AI chat response
Auth: Bearer token required
Body: {
  "user_input": string,
  "session_id": string,
  "context": string (optional)
}
Response: {
  "response": "AI generated response",
  "session_id": string,
  "context_used": [
    {
      "source": "document.pdf",
      "content": "relevant excerpt"
    }
  ],
  "timestamp": datetime,
  "tokens_used": 234
}
```

#### `POST /chat/close_session`
```
Purpose: End chat session
Auth: Bearer token required
Body: {
  "session_id": string
}
Response: {
  "message": "Session closed",
  "session_id": string
}
```

### Admin Endpoints

#### `POST /admin/upload_pdf`
```
Purpose: Upload PDF file
Auth: ADMIN token required
Content-Type: multipart/form-data
Form Data: file (PDF file)
Response: {
  "filename": string,
  "size": number,
  "location": "/all_documents/filename.pdf",
  "status": "success"
}
```

#### `GET /admin/get_all_docs`
```
Purpose: List all uploaded documents
Auth: ADMIN token required
Response: [
  {
    "filename": "doc1.pdf",
    "size": 1024000,
    "uploaded_at": datetime,
    "status": "ready"
  }
]
```

#### `POST /admin/update_selected_docs`
```
Purpose: Select documents for processing
Auth: ADMIN token required
Body: {
  "documents": ["doc1.pdf", "doc2.pdf"]
}
Response: {
  "selected_count": 2,
  "copied_files": ["doc1.pdf", "doc2.pdf"],
  "status": "success"
}
```

#### `POST /admin/ingest`
```
Purpose: Ingest selected documents to Pinecone
Auth: ADMIN token required
Body: {} (uses documents from input_documents/)
Response: {
  "documents_ingested": 2,
  "chunks_created": 45,
  "vectors_indexed": 45,
  "status": "success",
  "execution_time_seconds": 23
}
```

#### `POST /admin/generate_proposal`
```
Purpose: Generate sales proposal from documents
Auth: ADMIN token required
Body: {}
Response: {
  "proposal_id": string,
  "markdown_file": "proposal.md",
  "html_file": "proposal.html",
  "pdf_file": "proposal.pdf",
  "content_preview": "# Proposal\nSummary...",
  "generation_time_seconds": 45,
  "status": "success"
}
```

#### `GET /admin/get_selected_docs`
```
Purpose: Get currently selected documents
Auth: ADMIN token required
Response: [
  {
    "filename": "doc1.pdf",
    "size": 1024000,
    "selected_at": datetime
  }
]
```

#### `GET /admin/get_html_from_file`
```
Purpose: Retrieve HTML file content
Auth: ADMIN token required
Query Params: file=proposal.html
Response: HTML content (text/html)
```

#### `POST /admin/send_bulk_email`
```
Purpose: Send bulk emails
Auth: ADMIN token required
Body: {
  "recipients": ["email1@example.com", "email2@example.com"],
  "subject": "Subject line",
  "body": "Email body (supports HTML)",
  "template": "template_name (optional)"
}
Response: {
  "total_sent": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "recipient": "email1@example.com",
      "status": "sent",
      "timestamp": datetime
    }
  ]
}
```

#### `POST /admin/call`
```
Purpose: Initiate voice call
Auth: ADMIN token required
Body: {
  "phone_number": "+1234567890",
  "script": "Call script content",
  "context": "Additional context (optional)"
}
Response: {
  "call_id": "vapi-call-id",
  "phone_number": "+1234567890",
  "status": "initiated",
  "started_at": datetime
}
```

#### `GET /admin/get_last_summary`
```
Purpose: Get summary of last call
Auth: ADMIN token required
Response: {
  "call_id": "vapi-call-id",
  "phone_number": "+1234567890",
  "duration_seconds": 342,
  "summary": "Call summary text",
  "key_points": ["point1", "point2"],
  "status": "completed",
  "timestamp": datetime
}
```

#### `GET /admin/analytics`
```
Purpose: Get analytics data
Auth: ADMIN token required
Response: {
  "total_visitors": 1234,
  "total_leads": 456,
  "conversion_rate": 0.37,
  "average_session_duration": 245,
  "top_performing_products": [
    {
      "name": "Product A",
      "revenue": 50000,
      "units_sold": 250
    }
  ],
  "sales_by_country": {
    "US": 45000,
    "UK": 23000,
    "DE": 18000
  },
  "deal_status": {
    "pipeline": 15,
    "negotiation": 8,
    "closed": 20
  },
  "recent_leads": [
    {
      "name": "Lead Name",
      "email": "lead@example.com",
      "status": "interested",
      "created_at": datetime
    }
  ],
  "browser_sessions": {
    "Chrome": 650,
    "Firefox": 320,
    "Safari": 180
  },
  "top_queries": [
    {
      "query": "product pricing",
      "count": 234
    }
  ]
}
```

---

## Configuration & Environment

### Backend Configuration

#### **Environment Variables** (`.env` file)
```
# Database
CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/dbname

# LLM APIs
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...

# Vector Database
PINECONE_API_KEY=pc-...
INDEX_NAME=pravaha-documents

# Embeddings
COHERE_API_KEY=...

# Voice/Call
VAPI_API_KEY=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# Authentication
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=email@gmail.com
SMTP_PASSWORD=app-password
SMTP_FROM_EMAIL=noreply@pravaha.ai

# LangChain
LANGCHAIN_API_KEY=...
LANGCHAIN_TRACING=true

# Deployment
ENVIRONMENT=production|development

```

#### **CORS Configuration** (main.py)
```python
ALLOWED_ORIGINS = [
    "http://localhost:3000"]
```

#### **Session Configuration**
```python
SESSION_TIMEOUT = 3600  # 1 hour
MAX_SESSIONS_PER_USER = 5
SESSION_STORAGE = "mongodb"
```

### Frontend Configuration

#### **Next.js Config** (`next.config.mjs`)
```javascript
Configuration:
├── Image optimization enabled
├── Static generation enabled
├── API routes configured
├── Environment variables loaded
└── TypeScript strict mode
```

#### **TypeScript Config** (`tsconfig.json`)
```json
Paths:
{
  "@/*": ["./src/*"],
  "@/components/*": ["./src/components/*"],
  "@/lib/*": ["./src/lib/*"],
  "@/app/*": ["./src/app/*"]
}
```

#### **Tailwind Config** (`tailwind.config.ts`)
```typescript
Features:
├── Dark mode (class-based)
├── Custom font (Geist Sans, Geist Mono)
├── Custom animations
├── Extended color palette
└── Custom utilities
```

#### **Environment Variables** (`.env.local`)
```
NEXT_PUBLIC_API_URL=https://pravaha.onrender.com
NEXT_PUBLIC_APP_NAME=pravaha
NEXT_PUBLIC_APP_URL=https://pravaha.vercel.app
```

### Deployment Configuration

#### **Backend Deployment** (Procfile)
```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```
**Deployed on**: Render.com
**URL**: https://pravaha.onrender.com

#### **Frontend Deployment**
**Platform**: Vercel
**URL**: https://pravaha.vercel.app
**Build Command**: `npm run build`
**Start Command**: `npm start`

---

## Key Features

### 1. **AI-Powered Chat**
- Multi-turn conversations
- Document context injection (RAG)
- Session-based memory
- Real-time responses
- Text-to-speech output

### 2. **Document Management**
- PDF upload and storage
- Semantic document indexing (Pinecone)
- Context retrieval for conversations
- Document selection for proposals

### 3. **Intelligent Proposal Generation**
- Automatic PDF summarization
- LLM-based content generation
- Multi-format output (Markdown, HTML, PDF)
- Template-based customization

### 4. **Voice Call Automation**
- AI-driven phone calls (VAPI)
- Call routing (Twilio)
- Call summary extraction
- Recording and playback

### 5. **Email Campaigns**
- Bulk email sending
- Template personalization
- SMTP configuration
- HTML email support
- Delivery tracking

### 6. **Sales Analytics**
- Real-time metrics dashboard
- 12+ analytics widgets
- Sales pipeline tracking
- Lead management
- Geographic analytics
- Performance metrics

### 7. **Authentication & Security**
- JWT-based authentication
- Role-based access control
- Password hashing (bcrypt)
- Session management
- Protected routes

### 8. **Dark Mode**
- Automatic theme detection
- Manual toggle
- Persistent preference
- Full component support

---

## Deployment

### Frontend (Vercel)
```
Branch: main
Build: npm run build
Output: .next/
URL: https://pravaha.vercel.app
Environment:
  - NEXT_PUBLIC_API_URL
  - NEXT_PUBLIC_APP_NAME
  - NEXT_PUBLIC_APP_URL
```

### Backend (Render)
```
Framework: Python FastAPI
Build Command: pip install -r requirements_fixed.txt
Start Command: uvicorn backend.main:app --host 0.0.0.0
URL: https://pravaha.onrender.com
Port: 8000
Environment Variables: All .env variables
```

### Database (MongoDB)
```
Provider: MongoDB Atlas (cloud)
Connection: CONNECTION_STRING environment variable
Collections: chats, endpoints, proposal
```

### Vector Database (Pinecone)
```
Service: Pinecone Vector DB
Dimension: 1024
Metric: Cosine Similarity
Index: Defined in INDEX_NAME environment variable
```

---

## File Reference

### Backend Files Quick Reference

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `main.py` | FastAPI entry point | app, admin_router, chat_router |
| `userbot.py` | Alternative chatbot | Alternative implementation |
| `utils/chatbot.py` | AI conversation engine | ChatBot class |
| `utils/database.py` | MongoDB operations | Database class, CRUD ops |
| `utils/vectorbase.py` | RAG & vector search | PDFProcessor, retrievers |
| `utils/auth.py` | Authentication | JWT, OAuth2, password hashing |
| `utils/call.py` | Voice call integration | VAPICallManager |
| `utils/bulkEmailSend.py` | Email campaigns | BulkEmailSender |
| `routers/admin/upload.py` | Document upload | PDF upload, file management |
| `routers/admin/generate_proposal.py` | Proposal generation | Summarization, Markdown gen |
| `routers/admin/analytics.py` | Analytics data | Metrics aggregation |
| `routers/chat/response.py` | Chat handler | Query processing |

### Frontend Files Quick Reference

| File | Purpose | Key Exports |
|------|---------|------------|
| `app/page.tsx` | Landing page | Hero, Demos, Pricing |
| `app/(auth)/login/page.tsx` | Login page | Login form |
| `app/(auth)/signup/page.tsx` | Signup page | Registration form |
| `app/chat/page.tsx` | Chat interface | ChatBot UI |
| `app/dashboard/page.tsx` | Dashboard | Analytics dashboard |
| `app/dashboard/email/page.tsx` | Email interface | Email campaign UI |
| `app/dashboard/pdf/page.tsx` | PDF management | Upload, select, manage |
| `app/dashboard/voice/page.tsx` | Voice calls | Call interface |
| `components/analytics/*.tsx` | Analytics widgets | 12 dashboard components |
| `components/charts/*.tsx` | Chart components | 11 chart types |
| `components/ui/*.tsx` | shadcn/ui components | Primitive UI components |
| `lib/base-chart-options.ts` | Chart configuration | ApexCharts config factory |
| `lib/utils.ts` | Utility functions | Helper functions |

---

## Quick Navigation Guide

### For Questions About:

| Topic | Location | Files |
|-------|----------|-------|
| **Chat Functionality** | Backend | `utils/chatbot.py`, `routers/chat/response.py` |
| **Document Processing** | Backend | `utils/vectorbase.py`, `routers/admin/` |
| **Authentication** | Backend | `utils/auth.py`, `main.py` |
| **Database** | Backend | `utils/database.py` |
| **UI/Components** | Frontend | `components/`, `app/` |
| **Styling** | Frontend | `tailwind.config.ts`, `globals.css` |
| **API Integration** | Frontend | `app/chat/page.tsx`, `app/dashboard/` |
| **Voice Calls** | Backend | `utils/call.py`, `routers/admin/` |
| **Email** | Backend | `utils/bulkEmailSend.py`, `routers/admin/` |
| **Analytics** | Both | `routers/admin/analytics.py`, `components/analytics/` |

---

## Statistics

- **Total Files**: ~125
- **Python Files**: 19
- **TypeScript/TSX Files**: 84
- **Configuration Files**: 6
- **Images/Assets**: 15+
- **Lines of Code**: ~17,768
- **Frontend Components**: 50+
- **Backend Modules**: 10+
- **API Endpoints**: 20+
- **Database Collections**: 3
- **Deployment Services**: 2 (Vercel + Render)

---

## Quick Start Notes

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements_fixed.txt
# Configure .env file
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Access Points
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

**Generated**: March 17, 2026
**Indexed By**: Claude AI Agent
**Version**: 1.0
