# Testing

## Running Tests

```bash
# Run all backend tests
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
├── conftest.py          # Shared fixtures
├── test_router.py       # Router logic tests
├── test_knowledge.py    # Knowledge mapper tests
└── ...
```

## Fixtures

Shared fixtures are defined in `backend/tests/conftest.py`:

| Fixture | Description |
|---------|-------------|
| `sample_question` | A `Question` with topic "http_fundamentals", Bloom level "understand" |
| `sample_response` | A `Response` explaining GET vs POST differences |
| `sample_evaluation` | An `EvaluationResult` with confidence 0.7 and evidence |
| `sample_knowledge_graph` | A `KnowledgeGraph` with 2 nodes and 1 edge |
| `initial_state` | Fresh `AssessmentState` for "backend_engineering" domain |
| `mid_assessment_state` | `AssessmentState` mid-assessment with history and calibrated_level="mid" |

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

## CI Pipeline

Tests run automatically on every push and PR via GitHub Actions.

**Workflow**: `.github/workflows/ci.yml`

The CI pipeline runs three jobs:

### `backend-checks`
- Python 3.11
- `ruff check .` and `ruff format --check .` (lint + format)
- `pytest tests/` (tests)

### `frontend-checks`
- Node.js 20
- `npx eslint .` (lint)
- `npx tsc --noEmit` (type check)
- `npm run build` (build verification)

### `security`
- Gitleaks scanning for secrets
- Verification that no `.env` files (except `.env.example`) are committed

## Test Conventions

- Test files are named `test_*.py`
- Test functions are named `test_*`
- Use fixtures from `conftest.py` for shared state
- Mock external services (LLM calls) in unit tests
- Use `@pytest.mark.asyncio` for async tests
- Keep tests focused — one assertion per test where practical
