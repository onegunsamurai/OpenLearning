"""Tests for the branch router (deterministic routing logic)."""

from app.graph.router import MAX_TOPICS, decide_branch, get_deeper_bloom, get_next_topic
from app.graph.state import make_initial_state
from app.models.assessment_pipeline import AgendaItem, EvaluationResult, Question, TopicStatus
from app.models.bloom import BloomLevel
from app.models.knowledge import KnowledgeGraph, KnowledgeNode


def _make_state(**overrides):
    state = make_initial_state(
        candidate_id="test",
        skill_ids=["nodejs"],
        skill_domain="backend_engineering",
        target_level="mid",
    )
    state.update(overrides)
    return state


def _make_agenda(n: int, assessed: int = 0) -> list[AgendaItem]:
    """Create an agenda with n items, first `assessed` marked as assessed."""
    items = []
    for i in range(n):
        status = TopicStatus.assessed if i < assessed else TopicStatus.pending
        items.append(
            AgendaItem(
                concept=f"topic_{i}",
                level="junior",
                status=status,
                confidence=0.8 if status == TopicStatus.assessed else 0.0,
            )
        )
    return items


class TestDecideBranch:
    def test_conclude_when_max_topics_assessed(self):
        agenda = _make_agenda(20, assessed=MAX_TOPICS)
        state = _make_state(
            topic_agenda=agenda,
            topics_evaluated=[f"topic_{i}" for i in range(MAX_TOPICS)],
            question_history=[
                Question(
                    id=f"q-{i}",
                    topic=f"topic_{i}",
                    bloom_level=BloomLevel.apply,
                    text="Q?",
                    question_type="conceptual",
                )
                for i in range(MAX_TOPICS)
            ],
        )
        assert decide_branch(state) == "conclude"

    def test_conclude_when_question_budget_exhausted(self):
        agenda = _make_agenda(15, assessed=3)
        per_topic = 4  # standard
        max_total = min(len(agenda), MAX_TOPICS) * per_topic  # 10 * 4 = 40
        questions = [
            Question(
                id=f"q-{i}",
                topic="t",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
            for i in range(max_total)
        ]
        state = _make_state(
            topic_agenda=agenda,
            question_history=questions,
            topics_evaluated=["t1"],
            max_questions_per_topic=per_topic,
        )
        assert decide_branch(state) == "conclude"

    def test_deeper_when_high_confidence_and_room_to_bloom(self):
        agenda = _make_agenda(10, assessed=1)
        state = _make_state(
            topic_agenda=agenda,
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
        agenda = _make_agenda(10, assessed=1)
        state = _make_state(
            topic_agenda=agenda,
            current_topic="http_fundamentals",
            current_bloom_level=BloomLevel.apply,
            questions_on_current_topic=1,
            latest_evaluation=EvaluationResult(
                question_id="q-1",
                confidence=0.6,
                bloom_level=BloomLevel.understand,
                evidence=["Partial"],
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
        agenda = _make_agenda(10, assessed=1)
        state = _make_state(
            topic_agenda=agenda,
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
        agenda = _make_agenda(10, assessed=1)
        state = _make_state(
            topic_agenda=agenda,
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

    def test_conclude_when_no_remaining_topics(self):
        """All topics assessed or inferred, none pending/active — must conclude."""
        agenda = [
            AgendaItem(concept="a", level="junior", status=TopicStatus.assessed, confidence=0.8),
            AgendaItem(concept="b", level="junior", status=TopicStatus.assessed, confidence=0.7),
            AgendaItem(concept="c", level="junior", status=TopicStatus.inferred, confidence=0.4),
            AgendaItem(concept="d", level="mid", status=TopicStatus.inferred, confidence=0.3),
        ]
        state = _make_state(
            topic_agenda=agenda,
            topics_evaluated=["a", "b"],
            question_history=[
                Question(
                    id="q-1",
                    topic="a",
                    bloom_level=BloomLevel.apply,
                    text="Q?",
                    question_type="conceptual",
                )
            ],
            latest_evaluation=EvaluationResult(
                question_id="q-1",
                confidence=0.8,
                bloom_level=BloomLevel.apply,
                evidence=["Good", "Solid"],
            ),
        )
        # assessed_count=2 < MAX_TOPICS=10, question_history=1 < max_total
        # But no pending or active topics → should conclude
        assert decide_branch(state) == "conclude"

    def test_does_not_conclude_while_active_topic_exists(self):
        """An active topic should not trigger early conclusion."""
        agenda = [
            AgendaItem(concept="a", level="junior", status=TopicStatus.active),
        ]
        state = _make_state(
            topic_agenda=agenda,
            current_topic="a",
            current_bloom_level=BloomLevel.apply,
            questions_on_current_topic=1,
            latest_evaluation=EvaluationResult(
                question_id="q-1",
                confidence=0.8,
                bloom_level=BloomLevel.apply,
                evidence=["Good", "Solid"],
            ),
            knowledge_graph=KnowledgeGraph(
                nodes=[KnowledgeNode(concept="a", confidence=0.8, bloom_level=BloomLevel.apply)],
            ),
            question_history=[
                Question(
                    id="q-1",
                    topic="a",
                    bloom_level=BloomLevel.apply,
                    text="Q?",
                    question_type="conceptual",
                )
            ],
        )
        # Only 1 topic, it's active, 1 question asked — should deeper/probe, NOT conclude
        result = decide_branch(state)
        assert result != "conclude"

    def test_dynamic_budget_with_quick_thoroughness(self):
        """Quick thoroughness (2 per topic) exhausts budget faster."""
        agenda = _make_agenda(15, assessed=3)
        max_total = min(15, MAX_TOPICS) * 2  # 10 * 2 = 20
        questions = [
            Question(
                id=f"q-{i}",
                topic="t",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
            for i in range(max_total)
        ]
        state = _make_state(
            topic_agenda=agenda,
            question_history=questions,
            max_questions_per_topic=2,
        )
        assert decide_branch(state) == "conclude"


class TestGetNextTopic:
    def test_picks_first_pending_from_agenda(self):
        agenda = [
            AgendaItem(concept="a", level="junior", status=TopicStatus.assessed, confidence=0.8),
            AgendaItem(concept="b", level="junior", status=TopicStatus.inferred, confidence=0.4),
            AgendaItem(concept="c", level="junior", status=TopicStatus.pending),
        ]
        state = _make_state(topic_agenda=agenda, current_topic="a")
        result = get_next_topic(state)
        assert result["current_topic"] == "c"
        assert result["questions_on_current_topic"] == 0

    def test_marks_current_topic_as_assessed(self):
        agenda = [
            AgendaItem(concept="a", level="junior", status=TopicStatus.active),
            AgendaItem(concept="b", level="junior", status=TopicStatus.pending),
        ]
        state = _make_state(
            topic_agenda=agenda,
            current_topic="a",
            knowledge_graph=KnowledgeGraph(
                nodes=[KnowledgeNode(concept="a", confidence=0.75, bloom_level=BloomLevel.apply)],
            ),
        )
        result = get_next_topic(state)
        updated_agenda = result["topic_agenda"]
        a_item = next(i for i in updated_agenda if i.concept == "a")
        assert a_item.status == TopicStatus.assessed
        assert a_item.confidence == 0.75

    def test_skips_inferred_topics(self):
        agenda = [
            AgendaItem(concept="a", level="junior", status=TopicStatus.inferred, confidence=0.4),
            AgendaItem(concept="b", level="mid", status=TopicStatus.pending),
        ]
        state = _make_state(topic_agenda=agenda, current_topic="")
        result = get_next_topic(state)
        assert result["current_topic"] == "b"

    def test_returns_empty_when_all_covered(self):
        agenda = [
            AgendaItem(concept="a", level="junior", status=TopicStatus.assessed, confidence=0.8),
        ]
        state = _make_state(topic_agenda=agenda, current_topic="a")
        result = get_next_topic(state)
        assert result["current_topic"] == ""

    def test_marks_next_topic_as_active(self):
        agenda = [
            AgendaItem(concept="a", level="junior", status=TopicStatus.pending),
        ]
        state = _make_state(topic_agenda=agenda, current_topic="")
        result = get_next_topic(state)
        updated = result["topic_agenda"]
        assert updated[0].status == TopicStatus.active


class TestGetDeeperBloom:
    def test_advances_bloom_level(self):
        state = _make_state(current_bloom_level=BloomLevel.apply)
        result = get_deeper_bloom(state)
        assert result["current_bloom_level"] == BloomLevel.analyze

    def test_caps_at_create(self):
        state = _make_state(current_bloom_level=BloomLevel.create)
        result = get_deeper_bloom(state)
        assert result["current_bloom_level"] == BloomLevel.create
