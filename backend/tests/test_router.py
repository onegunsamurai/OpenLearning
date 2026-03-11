"""Tests for the branch router (deterministic routing logic)."""

from app.graph.router import decide_branch, get_deeper_bloom, get_next_topic
from app.graph.state import (
    BloomLevel,
    EvaluationResult,
    KnowledgeGraph,
    KnowledgeNode,
    Question,
    make_initial_state,
)


def _make_state(**overrides):
    state = make_initial_state(
        candidate_id="test",
        skill_ids=["nodejs"],
        skill_domain="backend_engineering",
        target_level="mid",
    )
    state.update(overrides)
    return state


class TestDecideBranch:
    def test_conclude_when_max_topics_reached(self):
        state = _make_state(
            topics_evaluated=["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"],
            question_history=[
                Question(
                    id=f"q-{i}",
                    topic=f"t{i}",
                    bloom_level=BloomLevel.apply,
                    text="Q?",
                    question_type="conceptual",
                )
                for i in range(8)
            ],
        )
        assert decide_branch(state) == "conclude"

    def test_conclude_when_max_questions_reached(self):
        questions = [
            Question(
                id=f"q-{i}",
                topic="t",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
            for i in range(25)
        ]
        state = _make_state(
            question_history=questions,
            topics_evaluated=["t1"],
        )
        assert decide_branch(state) == "conclude"

    def test_deeper_when_high_confidence_and_room_to_bloom(self):
        state = _make_state(
            current_topic="http_fundamentals",
            current_bloom_level=BloomLevel.apply,
            questions_on_current_topic=1,
            latest_evaluation=EvaluationResult(
                question_id="q-1",
                confidence=0.8,
                bloom_level=BloomLevel.apply,
                evidence=["Good", "Solid"],
            ),
            knowledge_graph=KnowledgeGraph(
                nodes=[
                    KnowledgeNode(
                        concept="http_fundamentals", confidence=0.8, bloom_level=BloomLevel.apply
                    )
                ],
                edges=[],
            ),
            topics_evaluated=["http_fundamentals"],
            question_history=[
                Question(
                    id="q-1",
                    topic="http_fundamentals",
                    bloom_level=BloomLevel.apply,
                    text="Q?",
                    question_type="conceptual",
                )
            ],
        )
        assert decide_branch(state) == "deeper"

    def test_probe_when_low_evidence(self):
        state = _make_state(
            current_topic="http_fundamentals",
            current_bloom_level=BloomLevel.apply,
            questions_on_current_topic=1,
            latest_evaluation=EvaluationResult(
                question_id="q-1",
                confidence=0.6,
                bloom_level=BloomLevel.understand,
                evidence=["Partial"],  # Only 1 evidence item
            ),
            knowledge_graph=KnowledgeGraph(
                nodes=[
                    KnowledgeNode(
                        concept="http_fundamentals",
                        confidence=0.5,
                        bloom_level=BloomLevel.understand,
                    )
                ],
                edges=[],
            ),
            topics_evaluated=["http_fundamentals"],
            question_history=[
                Question(
                    id="q-1",
                    topic="http_fundamentals",
                    bloom_level=BloomLevel.apply,
                    text="Q?",
                    question_type="conceptual",
                )
            ],
        )
        assert decide_branch(state) == "probe"

    def test_pivot_when_too_many_questions_on_topic(self):
        state = _make_state(
            current_topic="http_fundamentals",
            current_bloom_level=BloomLevel.apply,
            questions_on_current_topic=4,
            latest_evaluation=EvaluationResult(
                question_id="q-1",
                confidence=0.5,
                bloom_level=BloomLevel.understand,
                evidence=["Some", "Evidence"],
            ),
            knowledge_graph=KnowledgeGraph(
                nodes=[
                    KnowledgeNode(
                        concept="http_fundamentals",
                        confidence=0.5,
                        bloom_level=BloomLevel.understand,
                    )
                ],
                edges=[],
            ),
            topics_evaluated=["http_fundamentals"],
            question_history=[
                Question(
                    id="q-1",
                    topic="http_fundamentals",
                    bloom_level=BloomLevel.apply,
                    text="Q?",
                    question_type="conceptual",
                )
            ],
        )
        assert decide_branch(state) == "pivot"

    def test_pivot_when_low_confidence(self):
        state = _make_state(
            current_topic="http_fundamentals",
            current_bloom_level=BloomLevel.apply,
            questions_on_current_topic=1,
            latest_evaluation=EvaluationResult(
                question_id="q-1",
                confidence=0.2,
                bloom_level=BloomLevel.remember,
                evidence=["Wrong", "Confused"],
            ),
            knowledge_graph=KnowledgeGraph(
                nodes=[
                    KnowledgeNode(
                        concept="http_fundamentals", confidence=0.3, bloom_level=BloomLevel.remember
                    )
                ],
                edges=[],
            ),
            topics_evaluated=["http_fundamentals"],
            question_history=[
                Question(
                    id="q-1",
                    topic="http_fundamentals",
                    bloom_level=BloomLevel.apply,
                    text="Q?",
                    question_type="conceptual",
                )
            ],
        )
        assert decide_branch(state) == "pivot"


class TestGetNextTopic:
    def test_picks_first_unevaluated_topic(self):
        state = _make_state(
            topics_evaluated=["http_fundamentals"],
        )
        result = get_next_topic(state)
        assert result["current_topic"] != "http_fundamentals"
        assert result["current_topic"] != ""
        assert result["questions_on_current_topic"] == 0

    def test_resets_question_count(self):
        state = _make_state(topics_evaluated=[])
        result = get_next_topic(state)
        assert result["questions_on_current_topic"] == 0


class TestGetDeeperBloom:
    def test_advances_bloom_level(self):
        state = _make_state(current_bloom_level=BloomLevel.apply)
        result = get_deeper_bloom(state)
        assert result["current_bloom_level"] == BloomLevel.analyze

    def test_caps_at_create(self):
        state = _make_state(current_bloom_level=BloomLevel.create)
        result = get_deeper_bloom(state)
        assert result["current_bloom_level"] == BloomLevel.create
