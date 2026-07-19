# App Review Insights

AI-powered App Store review analysis platform. Collects user reviews via data import (JSON/CSV), then uses LLM to classify sentiment, extract actionable findings, generate product requirement documents (PRD), and produce test cases — all from real user feedback.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router) + TypeScript + Tailwind CSS 4 + React Query |
| Backend | FastAPI + Python 3.11+ |
| AI | OpenAI-compatible API (OpenAI / DeepSeek / any compatible provider) |
| Export | python-docx (DOCX), reportlab (PDF), Markdown |
| Streaming | Server-Sent Events (SSE) for real-time workflow progress |

## Architecture

```
app-review-insights/
├── backend/                    # FastAPI backend
│   ├── collector/              # Review collection (App Store RSS + data import)
│   ├── analyzer/               # Cleaner, Classifier, Finding Extractor
│   ├── planner/                # PRD Generator, Test Case Generator
│   ├── services/               # OpenAI client, Config
│   ├── schemas/                # Pydantic data models
│   ├── prompts/                # LLM prompt templates
│   ├── api/                    # FastAPI routes, workflow engine, export endpoints
│   └── data/                   # Data storage
├── frontend/                   # Next.js frontend
│   ├── app/                    # App Router pages & layout
│   ├── components/             # React components (ArtifactTabs, PRDView, FindingsList, etc.)
│   ├── services/               # API client (Axios + SSE streaming)
│   └── types/                  # TypeScript type definitions
└── docs/                       # Design & specification documents
```

## Features

- **Data Import** — Upload or paste JSON/CSV review data for instant analysis
- **App Store Collection** — Fetch reviews from Apple App Store (RSS feed; availability varies by app)
- **SSE Streaming** — Real-time workflow progress via Server-Sent Events with per-stage updates
- **6-Stage Pipeline** — Collect → Clean → Classify → Extract Findings → Generate PRD → Generate Test Cases
- **PRD Export** — Export PRD as Markdown, DOCX, or PDF with formatted templates
- **Interactive Traceability** — Clickable ID links across Findings → Requirements → Reviews → Test Cases with highlight navigation
- **Responsive UI** — Tailwind CSS 4 with dark-friendly design, animations, and stage-aware loading

## Workflow

```
Collect → Clean → Classify → Extract Findings → Generate PRD → Generate Test Cases
```

1. **Collect** — Import reviews (JSON/CSV) or fetch from App Store RSS feed
2. **Clean** — Remove duplicates and empty/invalid content
3. **Classify** — LLM dynamically discovers categories, assigns sentiment and confidence
4. **Extract Findings** — Aggregate classified reviews into actionable insights with severity and evidence
5. **Generate PRD** — Create structured product requirements with user stories and version plans
6. **Generate Test Cases** — Produce test cases linked to PRD requirements

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture & data flow |
| [DECISIONS.md](docs/DECISIONS.md) | Architecture Decision Records (ADR) |
| [PROJECT_SPEC.md](docs/PROJECT_SPEC.md) | Requirements & technical specifications |
| [PROMPTS.md](docs/PROMPTS.md) | LLM prompts & JSON Schema definitions |
| [TASKS.md](docs/TASKS.md) | Development task breakdown |

## Installation

### Prerequisites

- Python 3.11+
- Node.js 20+
- An OpenAI-compatible API key (OpenAI, DeepSeek, etc.)

### 1. Clone and configure

```bash
git clone <repo-url>
cd app-review-insights
cp .env.example backend/.env
```

Edit `backend/.env` and set your `OPENAI_API_KEY`. Adjust `OPENAI_MODEL` and `OPENAI_BASE_URL` if needed.

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

## Running

### Quick start (recommended)

**Linux / Mac:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```cmd
start.bat
```

### Manual start

**Backend** (terminal 1):
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend** (terminal 2):
```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** in your browser.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **Yes** | — | API key for LLM provider |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Model name |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | Base URL for API |
| `NEXT_PUBLIC_BACKEND_URL` | No | `http://localhost:8000` | Backend URL for frontend |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Allowed CORS origins (comma-separated) |

## API

Base URL: `http://localhost:8000`

### Health Check

```
GET /api/health
```

Response: `{ "status": "ok" }`

### Analyze Reviews

```
POST /api/analyze
Content-Type: application/json

{
  "url": "https://apps.apple.com/us/app/duolingo-language-lessons/id570060128",
  "goal": "Identify user pain points and feature requests"
}
```

Triggers the full 6-stage workflow. Returns per-stage status and artifact data.

Supports content negotiation:
- Default: synchronous `WorkflowResponse` (JSON)
- `Accept: text/event-stream`: SSE streaming response with real-time per-stage events

#### Import Data

```
POST /api/analyze/import
Content-Type: application/json

{
  "import_data": "[{\"id\":\"1\",\"rating\":5,\"content\":\"Great app!\",\"author\":\"User\",\"date\":\"2024-01-01\"}]",
  "goal": "Analyze user sentiment"
}
```

### Export PRD

```
POST /api/export/prd?format=pdf|docx|md
Content-Type: application/json

{ ... prd JSON object ... }
```

Returns the PRD as a downloadable file (`Content-Disposition: attachment`).

## License

MIT
