<<<<<<< HEAD
# DevPilot

AI-powered developer platform that analyzes your codebase and predicts the impact of every change.

## Prerequisites

- Node.js 18+
- Python 3.11+
- Docker & Docker Compose (for databases)

## Quick Start

### 1. Start databases

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.
The backend runs at `http://localhost:8000`.

### 4. Verify

- Health check: `curl http://localhost:8000/api/health`
- API docs: `http://localhost:8000/docs`

## Project Structure

```
devpilot/
├── frontend/          # Next.js + TypeScript
├── backend/           # FastAPI + Python
├── docs/              # Documentation
├── docker-compose.yml # Local databases
├── .env.example       # Environment template
└── README.md
```
=======
# DEVPILOT
>>>>>>> 44cedd436048fa06e64bd6ca7157b5e3bc7120dc
