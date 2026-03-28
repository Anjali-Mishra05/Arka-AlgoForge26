# AGENTS.md

## Scope

- This directory is the runnable Pravaha application.
- Read this file for any task under `Pravaha/`.
- For deeper guidance, also read the nearest leaf file:
  - `frontend/AGENTS.md`
  - `backend/AGENTS.md`

## Product Summary

Pravaha is an AI-powered sales platform with:

- a public landing page, auth pages, and pricing
- authenticated dashboard workflows for analytics, PDFs, proposals, calls, email, CRM, intelligence, and automations
- a public buyer-facing proposal page with lead capture and contextual chat
- a FastAPI backend with MongoDB persistence, vector search, proposal generation, call coaching, CRM sync, and internal automations

## Start Here

- Frontend shell and navigation: `frontend/src/components/AppShell.tsx`, `frontend/src/components/Sidebar.tsx`
- Frontend dashboard home: `frontend/src/app/dashboard/page.tsx`
- Frontend onboarding: `frontend/src/app/onboarding/page.tsx`
- Frontend public proposal view: `frontend/src/app/proposal/[id]/page.tsx`
- Frontend auth helpers: `frontend/src/lib/api.ts`, `frontend/src/lib/auth-client.ts`
- Backend app entrypoint: `backend/main.py`
- Backend admin router: `backend/routers/admin/__init__.py`
- Backend authenticated chat router: `backend/routers/chat/__init__.py`
- Backend public buyer chat: `backend/routers/chat/buyer_chat.py`
- Backend persistence: `backend/utils/database.py`

## Commands

- Frontend install: `npm install` in `frontend/`
- Frontend dev: `npm run dev`
- Frontend build: `npm run build`
- Frontend lint: `npm run lint`
- Backend venv: `python -m venv .venv` in `backend/`
- Backend install: `.venv\Scripts\activate` then `pip install -r requirements_fixed.txt`
- Backend dev: `uvicorn main:app --reload --host 127.0.0.1 --port 8000`

## Task Routing

- Marketing or pricing UI: start in `frontend/src/app/page.tsx` or `frontend/src/app/pricing/page.tsx`
- Auth flows: start in `frontend/src/app/(auth)/...` and `frontend/src/lib/auth-client.ts`
- Dashboard/admin workflows: start in the matching page under `frontend/src/app/dashboard/` and its backend endpoint under `backend/routers/admin/`
- Proposal sharing or buyer chat: start with `frontend/src/app/proposal/[id]/page.tsx`, `backend/routers/chat/buyer_chat.py`, and `backend/routers/admin/proposals.py`
- Call/coaching work: start with `frontend/src/components/component/voice-call.tsx`, `backend/routers/admin/call.py`, `backend/main.py`, `backend/utils/call.py`, and `backend/utils/coaching.py`
- CRM or automation work: start with `frontend/src/app/dashboard/settings/page.tsx` plus `backend/routers/admin/crm.py`, `backend/routers/admin/automations.py`, and the matching `backend/utils/` module
- Document ingestion or proposal generation: start with `backend/routers/admin/upload.py`, `backend/routers/admin/ingest.py`, `backend/routers/admin/generate_proposal.py`, `backend/utils/vectorbase.py`

## Search Discipline

- Do not search `frontend/node_modules/`, `frontend/.next/`, `backend/.venv/`, or `backend/__pycache__/`.
- Treat `backend/all_documents/` and `backend/input_documents/` as runtime storage, not source code, unless the task is explicitly about generated documents.
- Prefer following the request path from caller to callee before broad search.

## Compatibility Notes

- Auth and some legacy helpers use the global singleton `db = Database("pravaha")` in `backend/utils/database.py`.
- Most newer admin, proposal, onboarding, CRM, intelligence, and automation flows use `APP_DB_NAME` / `Database(APP_DB_NAME)` for `pravaha_app`.
- Treat the dual database naming as a compatibility boundary. Do not "clean it up" without tracing every caller.
- There is a maintained regression and integration test suite in this repo. Start with `TESTING.md`, `scripts/run_regression.py`, and `backend/tests/` when verifying changes.
