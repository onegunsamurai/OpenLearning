# OpenLearning

AI-powered learning engineering platform. Identify skill gaps and generate personalized learning plans.

## Features

- **Onboarding** — Paste a job description to auto-extract skills, or browse and select manually
- **Skill Assessment** — AI-powered chat interview that evaluates your proficiency across selected skills
- **Gap Analysis** — Radar chart visualization comparing current vs target proficiency with priority-ranked gaps
- **Learning Plan** — Phased, structured learning plan with theory, quiz, and lab modules

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- An Anthropic API key

### Setup

```bash
# Install all dependencies
make install

# Configure backend
cp backend/.env.example backend/.env
# Edit backend/.env and set ANTHROPIC_API_KEY

# Configure frontend
cp frontend/.env.example frontend/.env.local

# Run both servers
make dev
```

- Frontend: [http://localhost:3000](http://localhost:3000)
- Backend: [http://localhost:8000](http://localhost:8000)
- API docs: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

## Tech Stack

- **Backend**: Python FastAPI + LangChain + Anthropic Claude
- **Frontend**: Next.js 16 (App Router), TypeScript
- **Styling**: Tailwind CSS v4 + shadcn/ui
- **State**: Zustand (sessionStorage persistence)
- **Charts**: Recharts
- **Animations**: Motion (Framer Motion v11)

## Architecture

```
OpenLearning/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router mounts
│   │   ├── config.py            # Settings (API key, CORS origins)
│   │   ├── models/              # Pydantic models (OpenAPI source of truth)
│   │   ├── routes/              # API endpoints
│   │   ├── services/            # AI service layer
│   │   ├── data/                # Skills taxonomy
│   │   └── prompts/             # System prompts for Claude
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages (no API routes)
│   │   ├── components/          # UI components
│   │   ├── hooks/               # Custom hooks
│   │   └── lib/                 # Types, store, API client
│   └── package.json
├── scripts/
│   └── generate-types.sh        # OpenAPI → TypeScript types
└── Makefile
```

### API Endpoints

| Method | Path               | Description                    |
|--------|--------------------|--------------------------------|
| GET    | /api/skills        | List all skills and categories |
| POST   | /api/parse-jd      | Extract skills from job desc   |
| POST   | /api/assess        | Streaming skill assessment     |
| POST   | /api/gap-analysis  | Generate gap analysis          |
| POST   | /api/learning-plan | Generate learning plan         |

### Type Generation

Generate TypeScript types from the backend OpenAPI spec:

```bash
# With backend running
make generate-types
```
