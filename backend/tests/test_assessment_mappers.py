"""Tests for assessment mapper functions — pure data transformations."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models.assessment_api import KnowledgeGraphOut, LearningPlanOut
from app.models.bloom import BloomLevel
from app.models.gap_analysis import GapAnalysis
from app.models.knowledge import KnowledgeGraph, KnowledgeNode
from app.services.assessment_mappers import (
    build_gap_analysis_out,
    build_kg_out,
    build_learning_plan_out,
    build_proficiency_scores,
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

    def test_from_dict(self):
        data = {
            "summary": "Learn React",
            "total_hours": 20,
            "phases": [
                {
                    "phase_number": 1,
                    "title": "Basics",
                    "concepts": ["JSX"],
                    "rationale": "Foundation",
                    "resources": [
                        {"type": "doc", "title": "React Docs", "url": "https://react.dev"}
                    ],
                    "estimated_hours": 10,
                }
            ],
        }
        result = build_learning_plan_out(data)
        assert result.summary == "Learn React"
        assert len(result.phases) == 1
        assert result.phases[0].title == "Basics"
        assert result.phases[0].resources[0].url == "https://react.dev"

    def test_from_pydantic_model(self):
        phase = MagicMock()
        phase.phase_number = 1
        phase.title = "Deep Dive"
        phase.concepts = ["Hooks"]
        phase.rationale = "Core"
        resource = MagicMock()
        resource.type = "video"
        resource.title = "Tutorial"
        resource.url = None
        phase.resources = [resource]
        phase.estimated_hours = 5

        plan = MagicMock()
        plan.summary = "Focus"
        plan.total_hours = 5
        plan.phases = [phase]

        result = build_learning_plan_out(plan)
        assert result.total_hours == 5
        assert result.phases[0].resources[0].url is None


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
