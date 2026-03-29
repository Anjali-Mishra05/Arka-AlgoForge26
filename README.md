# Arka-AlgoForge26

## Project Overview

Pravaha is an AI-powered sales automation platform designed to streamline sales processes with intelligent automation, proposal generation, voice coaching, and CRM integration.

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Next.js 16 (TypeScript/React)
- **Database**: MongoDB Atlas
- **Vector DB**: Pinecone
- **LLM**: Groq (llama-3.3-70b-versatile)
- **Voice**: VAPI + Twilio
- **Auth**: JWT + OAuth2

## Project Structure

```
Pravaha/
├── backend/          # FastAPI server
├── frontend/         # Next.js application
├── scripts/          # Utility scripts
└── *.md              # Documentation
```

## Documentation

- [AGENTS.md](./Pravaha/AGENTS.md) - Architecture and team overvie
- [ABSTRACT.md](./Pravaha/ABSTRACT.md) - System architecture
- [IMPLEMENTATION_PLAN.md](./Pravaha/IMPLEMENTATION_PLAN.md) - Development roadmap
- [INDEX.md](./Pravaha/INDEX.md) - Codebase reference

## Getting Started

### Backend Setup
```bash
cd Pravaha/backend
pip install -r requirements_fixed.txt
uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd Pravaha/frontend
npm install
npm run dev
```

## Team

This project is submitted to AlgoForge26 hackathon.

## License

proprietary
