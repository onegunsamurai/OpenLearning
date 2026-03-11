# Installation

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| Anthropic API key | [Get one here](https://console.anthropic.com/) |

## Install Dependencies

```bash
git clone https://github.com/onegunsamurai/OpenLearning.git
cd OpenLearning

# Install both backend and frontend dependencies
make install
```

This runs:

- `pip install -r backend/requirements.txt` (Python packages)
- `npm install` in the `frontend/` directory (Node packages)

## Configure Environment

### Backend

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set your API key:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
CORS_ORIGINS=http://localhost:3000
```

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key (required) | — |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |

### Frontend

```bash
cp frontend/.env.example frontend/.env.local
```

The default configuration points to the local backend:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Start the Application

```bash
# Run both frontend and backend concurrently
make dev
```

This starts:

- **Backend**: [http://localhost:8000](http://localhost:8000) (FastAPI + Uvicorn)
- **Frontend**: [http://localhost:3000](http://localhost:3000) (Next.js dev server)
- **API Docs**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs) (Swagger UI)

You can also run them separately:

```bash
make dev-backend   # Backend only (port 8000)
make dev-frontend  # Frontend only (port 3000)
```

## Verify Installation

1. Open [http://localhost:8000/api/docs](http://localhost:8000/api/docs) — you should see the Swagger UI
2. Open [http://localhost:3000](http://localhost:3000) — you should see the OpenLearning onboarding page
3. Try the skills endpoint: `GET http://localhost:8000/api/skills` should return the skills taxonomy

!!! tip
    If the backend fails to start, check that your `ANTHROPIC_API_KEY` is set correctly in `backend/.env`. The database (SQLite) is created automatically on first run in the `data/` directory.
