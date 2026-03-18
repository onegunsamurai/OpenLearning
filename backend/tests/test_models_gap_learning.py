"""Tests for gap analysis and learning plan Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.assessment import ProficiencyScore
from app.models.gap_analysis import GapAnalysis, GapAnalysisRequest, GapItem
from app.models.learning_plan import LearningModule, LearningPlan, LearningPlanRequest, Phase


class TestGapModels:
    def test_gap_item_valid(self):
        item = GapItem(
            skill_id="react",
            skill_name="React",
            current_level=60,
            target_level=80,
            gap=20,
            priority="high",
            recommendation="Practice more",
        )
        assert item.skill_id == "react"
        assert item.priority == "high"

    def test_gap_item_invalid_priority_raises(self):
        with pytest.raises(ValidationError):
            GapItem(
                skill_id="react",
                skill_name="React",
                current_level=60,
                target_level=80,
                gap=20,
                priority="urgent",
                recommendation="Practice more",
            )

    def test_gap_analysis_camel_serialization(self):
        analysis = GapAnalysis(
            overall_readiness=75,
            summary="Good progress",
            gaps=[
                GapItem(
                    skill_id="react",
                    skill_name="React",
                    current_level=60,
                    target_level=80,
                    gap=20,
                    priority="high",
                    recommendation="Practice more",
                )
            ],
        )
        dumped = analysis.model_dump(by_alias=True)
        assert "overallReadiness" in dumped
        assert "skillId" in dumped["gaps"][0]
        assert "currentLevel" in dumped["gaps"][0]

    def test_gap_analysis_request_validates(self):
        score = ProficiencyScore(
            skill_id="react",
            skill_name="React",
            score=72,
            confidence=0.85,
            reasoning="Good",
        )
        req = GapAnalysisRequest(proficiency_scores=[score])
        assert len(req.proficiency_scores) == 1

    def test_gap_analysis_empty_gaps_valid(self):
        analysis = GapAnalysis(overall_readiness=100, summary="No gaps", gaps=[])
        assert analysis.gaps == []
        assert analysis.overall_readiness == 100


class TestLearningPlanModels:
    def test_learning_module_valid(self):
        mod = LearningModule(
            id="mod-1",
            title="React Basics",
            description="Learn React fundamentals",
            type="theory",
            phase=1,
            skill_ids=["react"],
            duration_hours=4,
            objectives=["Understand JSX"],
            resources=["https://react.dev"],
        )
        assert mod.type == "theory"
        assert mod.duration_hours == 4

    def test_learning_module_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            LearningModule(
                id="mod-1",
                title="React Basics",
                description="Learn React",
                type="exam",
                phase=1,
                skill_ids=["react"],
                duration_hours=4,
                objectives=["Understand JSX"],
                resources=["https://react.dev"],
            )

    def test_phase_valid(self):
        mod = LearningModule(
            id="mod-1",
            title="React Basics",
            description="Learn React",
            type="lab",
            phase=1,
            skill_ids=["react"],
            duration_hours=4,
            objectives=["Build a component"],
            resources=[],
        )
        phase = Phase(phase=1, name="Foundation", description="Build foundations", modules=[mod])
        assert phase.phase == 1
        assert len(phase.modules) == 1

    def test_learning_plan_camel_serialization(self):
        mod = LearningModule(
            id="mod-1",
            title="React Basics",
            description="Learn React",
            type="theory",
            phase=1,
            skill_ids=["react"],
            duration_hours=4,
            objectives=["Understand JSX"],
            resources=[],
        )
        phase = Phase(phase=1, name="Foundation", description="Build foundations", modules=[mod])
        plan = LearningPlan(
            title="React Plan",
            summary="Learn React",
            total_hours=20,
            total_weeks=4,
            phases=[phase],
        )
        dumped = plan.model_dump(by_alias=True)
        assert "totalHours" in dumped
        assert "totalWeeks" in dumped
        assert "skillIds" in dumped["phases"][0]["modules"][0]
        assert "durationHours" in dumped["phases"][0]["modules"][0]

    def test_learning_plan_request_requires_gap_analysis(self):
        gap = GapAnalysis(
            overall_readiness=50,
            summary="Needs work",
            gaps=[
                GapItem(
                    skill_id="react",
                    skill_name="React",
                    current_level=30,
                    target_level=80,
                    gap=50,
                    priority="critical",
                    recommendation="Study hard",
                )
            ],
        )
        req = LearningPlanRequest(gap_analysis=gap)
        assert req.gap_analysis.overall_readiness == 50
