"""Tests for state schema validation and instantiation."""

from app.graph.state import (
    BLOOM_ORDER,
    BloomLevel,
    EvaluationResult,
    KnowledgeGraph,
    KnowledgeNode,
    LearningPhase,
    LearningPlan,
    Question,
    Resource,
    bloom_index,
    make_initial_state,
)


class TestBloomLevel:
    def test_bloom_order_has_six_levels(self):
        assert len(BLOOM_ORDER) == 6

    def test_bloom_index_ordering(self):
        assert bloom_index(BloomLevel.remember) < bloom_index(BloomLevel.understand)
        assert bloom_index(BloomLevel.understand) < bloom_index(BloomLevel.apply)
        assert bloom_index(BloomLevel.apply) < bloom_index(BloomLevel.analyze)
        assert bloom_index(BloomLevel.analyze) < bloom_index(BloomLevel.evaluate)
        assert bloom_index(BloomLevel.evaluate) < bloom_index(BloomLevel.create)

    def test_bloom_from_string(self):
        assert BloomLevel("apply") == BloomLevel.apply


class TestQuestion:
    def test_create_question(self):
        q = Question(
            id="q-1",
            topic="http_fundamentals",
            bloom_level=BloomLevel.understand,
            text="What is HTTP?",
            question_type="conceptual",
        )
        assert q.id == "q-1"
        assert q.bloom_level == BloomLevel.understand

    def test_question_camel_serialization(self):
        q = Question(
            id="q-1",
            topic="test",
            bloom_level=BloomLevel.apply,
            text="Test?",
            question_type="code",
        )
        dumped = q.model_dump(by_alias=True)
        assert "bloomLevel" in dumped
        assert "questionType" in dumped


class TestKnowledgeGraph:
    def test_empty_graph(self):
        kg = KnowledgeGraph()
        assert kg.nodes == []
        assert kg.edges == []

    def test_get_node_found(self, sample_knowledge_graph):
        node = sample_knowledge_graph.get_node("http_fundamentals")
        assert node is not None
        assert node.confidence == 0.6

    def test_get_node_not_found(self, sample_knowledge_graph):
        node = sample_knowledge_graph.get_node("nonexistent")
        assert node is None

    def test_upsert_node_update(self, sample_knowledge_graph):
        updated = KnowledgeNode(
            concept="http_fundamentals",
            confidence=0.9,
            bloom_level=BloomLevel.apply,
            prerequisites=[],
            evidence=["Updated evidence"],
        )
        sample_knowledge_graph.upsert_node(updated)
        node = sample_knowledge_graph.get_node("http_fundamentals")
        assert node.confidence == 0.9

    def test_upsert_node_insert(self, sample_knowledge_graph):
        new_node = KnowledgeNode(
            concept="new_concept",
            confidence=0.5,
            bloom_level=BloomLevel.remember,
        )
        sample_knowledge_graph.upsert_node(new_node)
        assert sample_knowledge_graph.get_node("new_concept") is not None
        assert len(sample_knowledge_graph.nodes) == 3


class TestMakeInitialState:
    def test_creates_valid_state(self):
        state = make_initial_state(
            candidate_id="test",
            skill_ids=["nodejs"],
            skill_domain="backend_engineering",
        )
        assert state["candidate_id"] == "test"
        assert state["skill_ids"] == ["nodejs"]
        assert state["skill_domain"] == "backend_engineering"
        assert state["target_level"] == "mid"
        assert state["question_history"] == []
        assert state["assessment_complete"] is False

    def test_custom_target_level(self):
        state = make_initial_state(
            candidate_id="test",
            skill_ids=["nodejs"],
            skill_domain="backend_engineering",
            target_level="senior",
        )
        assert state["target_level"] == "senior"


class TestEvaluationResult:
    def test_create_evaluation(self):
        ev = EvaluationResult(
            question_id="q-1",
            confidence=0.8,
            bloom_level=BloomLevel.apply,
            evidence=["Good answer"],
        )
        assert ev.confidence == 0.8
        assert len(ev.evidence) == 1


class TestLearningPlan:
    def test_empty_plan(self):
        plan = LearningPlan(phases=[], total_hours=0, summary="No gaps")
        assert plan.total_hours == 0
        assert plan.phases == []

    def test_plan_with_phases(self):
        plan = LearningPlan(
            phases=[
                LearningPhase(
                    phase_number=1,
                    title="Foundations",
                    concepts=["http_fundamentals"],
                    rationale="Start with basics",
                    resources=[Resource(type="article", title="HTTP Guide")],
                    estimated_hours=5,
                )
            ],
            total_hours=5,
            summary="A basic plan",
        )
        assert len(plan.phases) == 1
        assert plan.phases[0].resources[0].type == "article"
