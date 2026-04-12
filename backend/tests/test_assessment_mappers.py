"""Tests for assessment mapper functions — pure data transformations."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.graph.state import BloomLevel, KnowledgeGraph, KnowledgeNode
from app.models.assessment_api import KnowledgeGraphOut, LearningPlanOut
from app.models.gap_analysis import GapAnalysis
from app.services.assessment_mappers import (
    build_gap_analysis_out,
    build_kg_out,
    build_learning_plan_out,
    build_proficiency_scores,
    normalize_phase_concepts,
    reconstruct_kg,
)

# ---------------------------------------------------------------------------
# build_kg_out
# ---------------------------------------------------------------------------


class TestBuildKgOut:
    def test_none_returns_empty(self):
        result = build_kg_out(None)
        assert isinstance(result, KnowledgeGraphOut)
        assert result.nodes == []

    def test_with_nodes(self):
        kg = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="react_hooks",
                    confidence=0.85,
                    bloom_level=BloomLevel.apply,
                    prerequisites=["basics"],
                    evidence=["Good"],
                ),
            ],
            edges=[],
        )
        result = build_kg_out(kg)
        assert len(result.nodes) == 1
        assert result.nodes[0].concept == "react_hooks"
        assert result.nodes[0].confidence == 0.85
        assert result.nodes[0].bloom_level == "apply"
        assert result.nodes[0].prerequisites == ["basics"]

    def test_handles_string_bloom_level(self):
        """When bloom_level is already a string (e.g., from a dict), handle gracefully."""
        node = MagicMock()
        node.concept = "test"
        node.confidence = 0.5
        node.bloom_level = "understand"  # string, not enum
        node.prerequisites = []
        kg = MagicMock()
        kg.nodes = [node]
        result = build_kg_out(kg)
        assert result.nodes[0].bloom_level == "understand"


# ---------------------------------------------------------------------------
# build_gap_analysis_out
# ---------------------------------------------------------------------------


class TestBuildGapAnalysisOut:
    def test_none_returns_defaults(self):
        result = build_gap_analysis_out(None)
        assert isinstance(result, GapAnalysis)
        assert result.overall_readiness == 0
        assert result.summary == ""
        assert result.gaps == []

    def test_from_dict(self):
        data = {
            "overall_readiness": 70,
            "summary": "Needs work",
            "gaps": [
                {
                    "skill_id": "react",
                    "skill_name": "React",
                    "current_level": 50,
                    "target_level": 80,
                    "gap": 30,
                    "priority": "high",
                    "recommendation": "Study more",
                }
            ],
        }
        result = build_gap_analysis_out(data)
        assert result.overall_readiness == 70
        assert len(result.gaps) == 1
        assert result.gaps[0].skill_id == "react"

    def test_from_pydantic_model(self):
        """When enriched is a Pydantic model (from live graph state)."""
        enriched = MagicMock()
        enriched.overall_readiness = 85
        enriched.summary = "Strong"
        gap = MagicMock()
        gap.skill_id = "ts"
        gap.skill_name = "TypeScript"
        gap.current_level = 60
        gap.target_level = 80
        gap.gap = 20
        gap.priority = "medium"
        gap.recommendation = "Practice generics"
        enriched.gaps = [gap]
        result = build_gap_analysis_out(enriched)
        assert result.overall_readiness == 85
        assert result.gaps[0].skill_id == "ts"


# ---------------------------------------------------------------------------
# build_learning_plan_out
# ---------------------------------------------------------------------------


class TestBuildLearningPlanOut:
    def test_none_returns_empty(self):
        result = build_learning_plan_out(None)
        assert isinstance(result, LearningPlanOut)
        assert result.summary == ""
        assert result.total_hours == 0
        assert result.phases == []

    def test_from_dict_new_shape(self):
        """DB JSONB row written in the post-#168 nested shape."""
        data = {
            "summary": "Learn React",
            "total_hours": 20,
            "phases": [
                {
                    "phase_number": 1,
                    "title": "Basics",
                    "rationale": "Foundation",
                    "concepts": [
                        {
                            "key": "jsx",
                            "name": "JSX",
                            "description": "Syntax extension for React.",
                            "resources": [
                                {
                                    "type": "doc",
                                    "title": "React Docs",
                                    "url": "https://react.dev",
                                }
                            ],
                        }
                    ],
                    "estimated_hours": 10,
                }
            ],
        }
        result = build_learning_plan_out(data)
        assert result.summary == "Learn React"
        assert len(result.phases) == 1
        assert result.phases[0].title == "Basics"
        assert len(result.phases[0].concepts) == 1
        concept = result.phases[0].concepts[0]
        assert concept.key == "jsx"
        assert concept.name == "JSX"
        assert concept.description == "Syntax extension for React."
        assert concept.resources[0].url == "https://react.dev"

    def test_build_learning_plan_out_legacy_dict_shape(self):
        """Regression: legacy JSONB rows (list[str] concepts + phase resources)
        must still render without error after the #168 reshape. Phase-level
        resources are dropped and concepts are promoted to empty-description
        ConceptOut objects.
        """
        legacy = {
            "summary": "Old plan",
            "total_hours": 5,
            "phases": [
                {
                    "phase_number": 1,
                    "title": "Phase One",
                    "rationale": "Legacy rationale",
                    "concepts": ["App Router", "Server Actions"],
                    "resources": [
                        {"type": "article", "title": "Legacy Article", "url": None},
                    ],
                    "estimated_hours": 5,
                }
            ],
        }
        result = build_learning_plan_out(legacy)
        assert len(result.phases) == 1
        phase = result.phases[0]
        assert len(phase.concepts) == 2
        assert phase.concepts[0].key == "app-router"
        assert phase.concepts[0].name == "App Router"
        assert phase.concepts[0].description == ""
        assert phase.concepts[0].resources == []
        assert phase.concepts[1].key == "server-actions"
        # Phase-level LearningPhaseOut no longer has a resources field
        assert not hasattr(phase, "resources") or getattr(phase, "resources", None) is None

    def test_legacy_dict_with_empty_concepts_does_not_crash(self):
        """Legacy row with an empty concepts list must not IndexError."""
        legacy = {
            "summary": "Empty phase plan",
            "total_hours": 0,
            "phases": [
                {
                    "phase_number": 1,
                    "title": "Empty",
                    "rationale": "",
                    "concepts": [],
                    "resources": [],
                    "estimated_hours": 0,
                }
            ],
        }
        result = build_learning_plan_out(legacy)
        assert result.phases[0].concepts == []

    def test_from_pydantic_model(self):
        resource = MagicMock()
        resource.type = "video"
        resource.title = "Tutorial"
        resource.url = None

        concept = MagicMock()
        concept.key = "hooks"
        concept.name = "Hooks"
        concept.description = "React hooks fundamentals."
        concept.resources = [resource]

        phase = MagicMock()
        phase.phase_number = 1
        phase.title = "Deep Dive"
        phase.concepts = [concept]
        phase.rationale = "Core"
        phase.estimated_hours = 5

        plan = MagicMock()
        plan.summary = "Focus"
        plan.total_hours = 5
        plan.phases = [phase]

        result = build_learning_plan_out(plan)
        assert result.total_hours == 5
        assert result.phases[0].concepts[0].key == "hooks"
        assert result.phases[0].concepts[0].name == "Hooks"
        assert result.phases[0].concepts[0].resources[0].url is None


# ---------------------------------------------------------------------------
# normalize_phase_concepts
# ---------------------------------------------------------------------------


class TestNormalizePhaseConcepts:
    """Direct tests for the JSONB back-compat helper used by both
    ``build_learning_plan_out`` and the markdown exporter. Covers the new
    nested shape, the legacy ``list[str]`` shape, and the mixed-type
    corruption edge case the shape detection must not silently promote.
    """

    def test_empty_concepts_returns_empty_list(self):
        assert normalize_phase_concepts({"phase_number": 1, "concepts": []}) == []

    def test_missing_concepts_key_returns_empty_list(self):
        assert normalize_phase_concepts({"phase_number": 1}) == []

    def test_new_shape_preserves_fields(self):
        result = normalize_phase_concepts(
            {
                "phase_number": 1,
                "concepts": [
                    {
                        "key": "event-loop",
                        "name": "Event Loop",
                        "description": "How it schedules coroutines.",
                        "resources": [
                            {"type": "article", "title": "Primer", "url": "https://ex.com/el"}
                        ],
                    }
                ],
            }
        )
        assert len(result) == 1
        assert result[0]["key"] == "event-loop"
        assert result[0]["name"] == "Event Loop"
        assert result[0]["description"] == "How it schedules coroutines."
        assert result[0]["resources"][0]["title"] == "Primer"

    def test_new_shape_fills_missing_key_from_name(self):
        """A concept dict without an explicit `key` field should fall back to
        ``slugify_concept(name)`` — the same derivation ``plan_generator`` uses."""
        result = normalize_phase_concepts(
            {
                "phase_number": 1,
                "concepts": [
                    {"name": "Async I/O & Streams", "description": "", "resources": []},
                ],
            }
        )
        assert result[0]["key"] == "async-i-o-streams"

    def test_legacy_list_str_promotes_with_empty_fields(self):
        """Legacy JSONB rows store ``concepts: list[str]`` — the helper must
        promote each string to a concept dict with empty description/resources.
        Phase-level ``resources`` on the same row is intentionally dropped."""
        result = normalize_phase_concepts(
            {
                "phase_number": 2,
                "concepts": ["App Router", "Server Actions"],
                "resources": [{"type": "article", "title": "Dropped", "url": None}],
            }
        )
        assert len(result) == 2
        assert result[0] == {
            "key": "app-router",
            "name": "App Router",
            "description": "",
            "resources": [],
        }
        assert result[1]["key"] == "server-actions"

    def test_null_description_coerced_to_empty_string(self):
        """JSONB row with ``description: null`` must not propagate None into
        ConceptOut (which expects a string)."""
        result = normalize_phase_concepts(
            {
                "phase_number": 1,
                "concepts": [
                    {"key": "hooks", "name": "Hooks", "description": None, "resources": []},
                ],
            }
        )
        assert result[0]["description"] == ""

    def test_null_resources_coerced_to_empty_list(self):
        """JSONB row with ``resources: null`` must not cause a TypeError."""
        result = normalize_phase_concepts(
            {
                "phase_number": 1,
                "concepts": [
                    {"key": "hooks", "name": "Hooks", "description": "Desc", "resources": None},
                ],
            }
        )
        assert result[0]["resources"] == []

    def test_non_dict_resource_entries_filtered_out(self):
        """If a resources list contains non-dict entries (corruption), they
        should be silently dropped rather than causing a downstream error."""
        result = normalize_phase_concepts(
            {
                "phase_number": 1,
                "concepts": [
                    {
                        "key": "hooks",
                        "name": "Hooks",
                        "description": "",
                        "resources": [
                            {"type": "article", "title": "Good", "url": None},
                            "bad-entry",
                            42,
                        ],
                    },
                ],
            }
        )
        assert len(result[0]["resources"]) == 1
        assert result[0]["resources"][0]["title"] == "Good"

    def test_concepts_not_a_list_returns_empty_and_logs(self, caplog):
        """If concepts is a bare string or dict (corruption), must not iterate
        characters/keys into concept entries."""
        import logging

        with caplog.at_level(logging.WARNING):
            result = normalize_phase_concepts({"phase_number": 1, "concepts": "corrupted string"})
        assert result == []
        assert any(
            "learning_plan.concepts_invalid_container" in rec.message for rec in caplog.records
        )

    def test_null_name_coerced_to_empty_string(self):
        """If name is None, it must not crash slugify_concept."""
        result = normalize_phase_concepts(
            {
                "phase_number": 1,
                "concepts": [
                    {"key": "explicit-key", "name": None, "description": "", "resources": []},
                ],
            }
        )
        assert result[0]["key"] == "explicit-key"
        assert result[0]["name"] == ""

    def test_missing_name_and_key_does_not_crash(self):
        """A concept dict with neither name nor key must not raise."""
        result = normalize_phase_concepts(
            {
                "phase_number": 1,
                "concepts": [{"description": "Orphan", "resources": []}],
            }
        )
        assert result[0]["name"] == ""
        assert result[0]["key"] == ""

    def test_mixed_type_list_drops_phase_concepts_and_logs_warning(self, caplog):
        """A corrupted row with mixed dict/str concepts must not silently render
        partial cards. The helper drops the phase's concepts and logs a warning
        so the bad row is visible in logs without taking down the whole response.
        """
        import logging

        with caplog.at_level(logging.WARNING):
            result = normalize_phase_concepts(
                {
                    "phase_number": 3,
                    "concepts": [
                        "Legacy Name",
                        {"key": "new-shape", "name": "New Shape", "resources": []},
                    ],
                }
            )
        assert result == []
        assert any(
            "learning_plan.concepts_mixed_or_unknown" in rec.message for rec in caplog.records
        )


# ---------------------------------------------------------------------------
# build_proficiency_scores
# ---------------------------------------------------------------------------


class TestBuildProficiencyScores:
    def test_empty_kg(self):
        assert build_proficiency_scores({}) == []
        assert build_proficiency_scores({"knowledge_graph": None}) == []

    def test_computes_correctly(self):
        kg = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="react_hooks",
                    confidence=0.85,
                    bloom_level=BloomLevel.apply,
                    prerequisites=[],
                    evidence=["Uses useState", "Understands useEffect", "Custom hooks"],
                ),
            ],
            edges=[],
        )
        scores = build_proficiency_scores({"knowledge_graph": kg})
        assert len(scores) == 1
        assert scores[0].skill_id == "react_hooks"
        assert scores[0].score == 85
        assert scores[0].confidence == 0.85
        assert "Uses useState" in scores[0].reasoning

    def test_no_evidence_uses_default(self):
        kg = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="test",
                    confidence=0.5,
                    bloom_level=BloomLevel.remember,
                    prerequisites=[],
                    evidence=[],
                ),
            ],
            edges=[],
        )
        scores = build_proficiency_scores({"knowledge_graph": kg})
        assert scores[0].reasoning == "Assessed during evaluation"


# ---------------------------------------------------------------------------
# reconstruct_kg
# ---------------------------------------------------------------------------


class TestReconstructKg:
    def test_none_returns_empty(self):
        result = reconstruct_kg(None)
        assert isinstance(result, KnowledgeGraph)
        assert result.nodes == []

    def test_empty_dict_returns_empty(self):
        result = reconstruct_kg({})
        assert result.nodes == []

    def test_with_nodes(self):
        data = {
            "nodes": [
                {
                    "concept": "react",
                    "confidence": 0.8,
                    "bloom_level": "apply",
                    "prerequisites": [],
                    "evidence": ["Good"],
                }
            ],
            "edges": [("a", "b")],
        }
        result = reconstruct_kg(data)
        assert len(result.nodes) == 1
        assert result.nodes[0].concept == "react"
        assert result.nodes[0].bloom_level == BloomLevel.apply
        assert result.edges == [("a", "b")]

    def test_invalid_bloom_level_falls_back(self):
        data = {
            "nodes": [
                {
                    "concept": "test",
                    "confidence": 0.5,
                    "bloom_level": "INVALID_LEVEL",
                    "prerequisites": [],
                }
            ],
            "edges": [],
        }
        result = reconstruct_kg(data)
        assert result.nodes[0].bloom_level == BloomLevel.remember

    def test_missing_bloom_level_defaults(self):
        data = {
            "nodes": [{"concept": "test", "confidence": 0.5, "prerequisites": []}],
            "edges": [],
        }
        result = reconstruct_kg(data)
        assert result.nodes[0].bloom_level == BloomLevel.remember
