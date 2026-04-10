"""Tests for gap analysis Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.assessment import ProficiencyScore
from app.models.gap_analysis import GapAnalysis, GapAnalysisRequest, GapItem


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
