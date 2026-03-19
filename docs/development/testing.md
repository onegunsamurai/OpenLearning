# Testing

## Running Tests

```bash
# Run all tests (backend + frontend)
make test

# Run with verbose output
cd backend && pytest tests/ -v

# Run a specific test file
cd backend && pytest tests/test_router.py -v

# Run all checks (lint + typecheck + test)
make check
```

## Test Structure

Tests live in `backend/tests/` and use pytest with pytest-asyncio for async test support.

```
backend/tests/
├── conftest.py                # Shared fixtures, DB infrastructure, seed helpers
├── test_agents.py             # LLM agent tests (evaluator, question gen, knowledge mapper)
├── test_assessment_routes.py  # Assessment endpoint tests (start, respond, graph, report)
├── test_auth.py               # Auth endpoint tests (login, callback, me, logout, API key)
├── test_auth_guard.py         # Auth guard tests (protected route 401/403 behavior)
├── test_crypto.py             # Fernet encryption/decryption tests
├── test_db.py                 # Database tests
├── test_export.py             # Assessment report export tests
├── test_gap_analysis_route.py # Gap analysis endpoint tests
├── test_health.py             # Health endpoint tests
├── test_knowledge_base.py     # Knowledge base loader and mapper tests
├── test_learning_plan_route.py # Learning plan endpoint tests
├── test_models_gap_learning.py # Gap/learning plan model validation tests
├── test_parse_json_response.py # JSON response parser edge-case tests
├── test_pipeline.py           # LangGraph pipeline tests
├── test_retry.py              # Retry configuration and ainvoke_structured tests
├── test_roles.py              # Roles endpoint and YAML validation tests
├── test_router.py             # Router logic tests
├── test_session_cleanup.py    # Session timeout cleanup tests
├── test_state.py              # Assessment state tests
└── test_structured_output.py  # LLM output schema validation tests
```

## Fixtures

Shared fixtures are defined in `backend/tests/conftest.py`:

| Fixture / Export | Description |
|---------|-------------|
| `sample_question` | A `Question` with topic "http_fundamentals", Bloom level "understand" |
| `sample_response` | A `Response` explaining GET vs POST differences |
| `sample_evaluation` | An `EvaluationResult` with confidence 0.7 and evidence |
| `sample_knowledge_graph` | A `KnowledgeGraph` with 2 nodes and 1 edge |
| `initial_state` | Fresh `AssessmentState` for "backend_engineering" domain |
| `mid_assessment_state` | `AssessmentState` mid-assessment with history and calibrated_level="mid" |
| `setup_db` | Creates in-memory SQLite tables before each test, drops after |
| `_test_user` | An `AuthUser` with test user ID and username (module-level constant) |
| `_override_get_current_user` | Dependency override that returns `_test_user`, bypassing real JWT auth |
| `_test_app` | FastAPI app with assessment, gap_analysis, learning_plan, and auth routers (shared across route tests) |
| `seed_session()` | Helper to insert an `AssessmentSession` row |
| `seed_result()` | Helper to insert an `AssessmentResult` row with sample data |
| `mock_llm_response()` | Helper returning an `AsyncMock` chat model with given response text |
| `FULL_KNOWLEDGE_GRAPH` | Sample knowledge graph dict (React Hooks, TypeScript Generics) |
| `FULL_PROFICIENCY_SCORES` | Sample proficiency scores list |

## Writing Tests

### Unit Test Example

```python
import pytest
from app.graph.router import decide_branch

def test_conclude_when_max_topics(mid_assessment_state):
    """Should conclude when enough topics are evaluated."""
    state = mid_assessment_state
    state["topics_evaluated"] = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"]
    assert decide_branch(state) == "conclude"
```

### Async Test Example

```python
import pytest

@pytest.mark.asyncio
async def test_evaluate_response(mid_assessment_state):
    """Test response evaluation with mocked LLM."""
    # ... test implementation
```

### Using Fixtures

Fixtures are injected by name:

```python
def test_knowledge_graph_update(initial_state, sample_evaluation):
    state = initial_state
    state["latest_evaluation"] = sample_evaluation
    # ... assertions
```

## Frontend (TypeScript)

### Setup

Frontend tests use **Vitest** with jsdom environment and React Testing Library. Configuration is in `frontend/vitest.config.ts`.

```bash
# Run frontend tests (single run)
cd frontend && npm test

# Run in watch mode
cd frontend && npx vitest

# Or via Makefile
make test-frontend
```

### Test File Conventions

Test files are co-located next to their source files with a `.test.ts` or `.test.tsx` extension:

```
frontend/src/
├── app/
│   ├── page.test.tsx
│   ├── assess/
│   │   └── page.test.tsx
│   ├── demo/
│   │   ├── page.test.tsx
│   │   ├── assess/
│   │   │   └── page.test.tsx
│   │   └── report/
│   │       └── page.test.tsx
│   ├── export/
│   │   └── [id]/
│   │       └── page.test.tsx
│   ├── gap-analysis/
│   │   └── page.test.tsx
│   └── learning-plan/
│       └── page.test.tsx
├── components/
│   ├── assessment/
│   │   └── ChatMessage.test.tsx
│   ├── demo/
│   │   └── DemoOnboardingDialog.test.tsx
│   ├── gap-analysis/
│   │   ├── GapSummary.test.tsx
│   │   └── RadarChart.test.tsx
│   ├── layout/
│   │   └── PageShell.test.tsx
│   └── onboarding/
│       ├── SkillBrowser.test.tsx
│       └── role-selector.test.tsx
├── hooks/
│   ├── useAssessmentChat.test.ts
│   ├── useAuth.test.ts
│   └── useDemoAssessmentChat.test.ts
└── lib/
    ├── api.test.ts
    ├── auth-store.test.ts
    ├── store.test.ts
    └── demo/
        └── demo-assessment.test.ts
```

### Configuration

- **Environment:** jsdom
- **Globals:** Enabled — no need to import `describe`, `it`, `expect`
- **Path alias:** `@/` maps to `./src/*` (same as Next.js config)
- **Setup file:** `frontend/vitest.setup.ts`

### Writing Frontend Tests

```typescript
import { render, screen } from "@testing-library/react";
import { ChatMessage } from "./ChatMessage";

describe("ChatMessage", () => {
  it("renders user message", () => {
    render(<ChatMessage role="user" content="Hello" />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });
});
```

- Use `vi.mock()` for module mocking (must appear before imports of the mocked module)
- Query components by role/text, not test IDs
- Clean up `sessionStorage` and Zustand store state between tests

## CI Pipeline

Tests run automatically on every push and PR via GitHub Actions.

**Workflow**: `.github/workflows/ci.yml`

The CI pipeline runs five jobs:

### `backend-checks`
- Python 3.11
- `ruff check .` and `ruff format --check .` (lint + format)
- `pytest tests/` (tests)

### `frontend-checks`
- Node.js 20
- `npx eslint .` (lint)
- `npx tsc --noEmit` (type check)
- `npm test` (tests)
- `npm run build` (build verification)

### `security`
- Gitleaks scanning for secrets
- Verification that no `.env` files (except `.env.example`) are committed

### `docs-build`
- Runs only when `docs/**` or `mkdocs.yml` change
- `mkdocs build --strict` (validates docs build)

### `docker-build`
- Runs only when `Dockerfile`, `docker-compose*.yml`, or `.dockerignore` change
- `docker compose build` (validates Docker images build)

## Test Conventions

- Test files are named `test_*.py`
- Test functions are named `test_*`
- Use fixtures from `conftest.py` for shared state
- Mock external services (LLM calls) in unit tests
- Use `@pytest.mark.asyncio` for async tests
- Keep tests focused — one assertion per test where practical
