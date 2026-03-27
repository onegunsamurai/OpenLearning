from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db import AssessmentResult, AssessmentSession, AuthMethod, Base, get_db
from app.deps import AuthUser, get_current_user, get_user_api_key
from app.graph.state import (
    AssessmentState,
    BloomLevel,
    EvaluationResult,
    KnowledgeGraph,
    KnowledgeNode,
    Question,
    Response,
    make_initial_state,
)
from app.main import register_anthropic_error_handlers
from app.routes.assessment import router as assessment_router
from app.routes.auth import router as auth_router
from app.routes.gap_analysis import router as gap_analysis_router
from app.routes.learning_plan import router as learning_plan_router
from app.routes.user import router as user_router

# ── PostgreSQL test database ──────────────────────────────────────────────

_test_db_url = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://openlearning:openlearning@localhost:5432/openlearning_test",
)

_test_engine = create_async_engine(_test_db_url, poolclass=NullPool)
_TestSessionFactory = async_sessionmaker(_test_engine, expire_on_commit=False)


async def _override_get_db():
    async with _TestSessionFactory() as session:
        yield session


# ── Shared test app with all routers ────────────────────────────────────

_test_user = AuthUser(user_id="test-user-id", display_name="testuser", avatar_url="")


async def _override_get_current_user() -> AuthUser:
    return _test_user


async def _override_get_user_api_key() -> str:
    return "sk-test-key-for-tests"


_test_app = FastAPI()
_test_app.include_router(assessment_router, prefix="/api")
_test_app.include_router(gap_analysis_router, prefix="/api")
_test_app.include_router(learning_plan_router, prefix="/api")
_test_app.include_router(auth_router, prefix="/api/auth")
_test_app.include_router(user_router, prefix="/api/user")
_test_app.dependency_overrides[get_db] = _override_get_db
_test_app.dependency_overrides[get_current_user] = _override_get_current_user
_test_app.dependency_overrides[get_user_api_key] = _override_get_user_api_key

_mock_graph = AsyncMock()
_test_app.state.graph = _mock_graph

register_anthropic_error_handlers(_test_app)

# ── Sample data constants ───────────────────────────────────────────────

FULL_KNOWLEDGE_GRAPH = {
    "nodes": [
        {
            "concept": "React Hooks",
            "confidence": 0.85,
            "bloom_level": "apply",
            "prerequisites": [],
            "evidence": ["Demonstrated useState usage", "Explained useEffect"],
        },
        {
            "concept": "TypeScript Generics",
            "confidence": 0.7,
            "bloom_level": "apply",
            "prerequisites": ["React Hooks"],
            "evidence": [],
        },
    ]
}

FULL_GAP_NODES = [
    {
        "concept": "Next.js App Router",
        "confidence": 0.6,
        "bloom_level": "apply",
        "prerequisites": ["React Hooks"],
    }
]

FULL_LEARNING_PLAN = {
    "summary": "Focus on deepening Next.js knowledge.",
    "total_hours": 20,
    "phases": [
        {
            "phase_number": 1,
            "title": "Next.js Deep Dive",
            "estimated_hours": 16,
            "rationale": "Biggest gap relative to target level",
            "concepts": ["App Router", "Server Actions"],
            "resources": [
                {
                    "title": "Next.js Docs",
                    "url": "https://nextjs.org/docs",
                    "type": "documentation",
                },
                {"title": "Internal Guide", "url": None, "type": "guide"},
            ],
        }
    ],
}

FULL_PROFICIENCY_SCORES = [
    {
        "skill_id": "react",
        "skill_name": "React",
        "score": 72,
        "confidence": 0.85,
        "bloom_level": "apply",
    }
]

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def setup_db():
    """Create tables before each test, seed test user, drop after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    # Seed the default test user so FK constraints are satisfied
    from app.db import User

    async with _TestSessionFactory() as session:
        user = User(
            id="test-user-id",
            display_name="testuser",
            avatar_url="",
        )
        session.add(user)
        await session.flush()
        session.add(
            AuthMethod(
                user_id="test-user-id",
                provider="github",
                provider_id="99999",
            )
        )
        await session.commit()
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Seed helpers ────────────────────────────────────────────────────────


async def seed_session(
    db: AsyncSession,
    session_id: str = "sess-001",
    thread_id: str = "thread-001",
    status: str = "active",
    user_id: str = "test-user-id",
    role_id: str | None = None,
) -> str:
    session = AssessmentSession(
        session_id=session_id,
        thread_id=thread_id,
        skill_ids=["react"],
        target_level="mid",
        role_id=role_id,
        status=status,
        user_id=user_id,
    )
    db.add(session)
    await db.commit()
    return session_id


async def seed_result(
    db: AsyncSession,
    session_id: str = "sess-001",
    knowledge_graph: dict | None = None,
    gap_nodes: list | None = None,
    learning_plan: dict | None = None,
    proficiency_scores: list | None = None,
) -> None:
    result = AssessmentResult(
        session_id=session_id,
        knowledge_graph=knowledge_graph if knowledge_graph is not None else FULL_KNOWLEDGE_GRAPH,
        gap_nodes=gap_nodes if gap_nodes is not None else FULL_GAP_NODES,
        learning_plan=learning_plan if learning_plan is not None else FULL_LEARNING_PLAN,
        proficiency_scores=(
            proficiency_scores if proficiency_scores is not None else FULL_PROFICIENCY_SCORES
        ),
    )
    db.add(result)
    await db.commit()


# ── Mock helpers ────────────────────────────────────────────────────────


def mock_llm_response(text: str) -> AsyncMock:
    """Return an AsyncMock chat model whose ainvoke returns a message with given text."""
    mock_model = AsyncMock()
    mock_response = AsyncMock()
    mock_response.content = text
    mock_model.ainvoke.return_value = mock_response
    return mock_model


# ── State fixtures (from original conftest) ─────────────────────────────


@pytest.fixture
def sample_question() -> Question:
    return Question(
        id="q-1",
        topic="http_fundamentals",
        bloom_level=BloomLevel.understand,
        text="Explain the difference between GET and POST HTTP methods.",
        question_type="conceptual",
    )


@pytest.fixture
def sample_response() -> Response:
    return Response(
        question_id="q-1",
        text="GET is for retrieving data and is idempotent. POST is for creating resources and can have side effects.",
    )


@pytest.fixture
def sample_evaluation() -> EvaluationResult:
    return EvaluationResult(
        question_id="q-1",
        confidence=0.7,
        bloom_level=BloomLevel.understand,
        evidence=["Correctly identified idempotency", "Mentioned side effects"],
    )


@pytest.fixture
def sample_knowledge_graph() -> KnowledgeGraph:
    return KnowledgeGraph(
        nodes=[
            KnowledgeNode(
                concept="http_fundamentals",
                confidence=0.6,
                bloom_level=BloomLevel.understand,
                prerequisites=[],
                evidence=["Correctly identified idempotency"],
            ),
            KnowledgeNode(
                concept="rest_api_basics",
                confidence=0.4,
                bloom_level=BloomLevel.remember,
                prerequisites=["http_fundamentals"],
                evidence=["Partial understanding"],
            ),
        ],
        edges=[("http_fundamentals", "rest_api_basics")],
    )


@pytest.fixture
def initial_state() -> AssessmentState:
    return make_initial_state(
        candidate_id="test-candidate",
        skill_ids=["nodejs", "rest-api", "sql"],
        skill_domain="backend_engineering",
        target_level="mid",
    )


@pytest.fixture
def mid_assessment_state(
    initial_state, sample_question, sample_response, sample_evaluation, sample_knowledge_graph
) -> AssessmentState:
    """State as if we're mid-assessment with some history."""
    state = dict(initial_state)
    state["calibrated_level"] = "mid"
    state["current_topic"] = "http_fundamentals"
    state["current_bloom_level"] = BloomLevel.apply
    state["question_history"] = [sample_question]
    state["response_history"] = [sample_response]
    state["latest_evaluation"] = sample_evaluation
    state["knowledge_graph"] = sample_knowledge_graph
    state["topics_evaluated"] = ["http_fundamentals"]
    state["questions_on_current_topic"] = 1
    return state
