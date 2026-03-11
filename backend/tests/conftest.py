from __future__ import annotations

import pytest

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
