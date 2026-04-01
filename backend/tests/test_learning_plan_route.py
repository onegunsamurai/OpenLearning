"""Tests for the learning plan route."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.schemas import (
    LearningPlanModuleOutput,
    LearningPlanOutput,
    LearningPlanPhaseOutput,
)
from tests.conftest import _test_app


def _valid_plan_output() -> LearningPlanOutput:
    return LearningPlanOutput(
        title="TypeScript Mastery Plan",
        summary="A focused plan for TypeScript improvement",
        total_hours=30,
        total_weeks=4,
        phases=[
            LearningPlanPhaseOutput(
                phase=1,
                name="Foundations",
                description="Build core TypeScript skills",
                modules=[
                    LearningPlanModuleOutput(
                        id="mod-1",
                        title="TypeScript Basics",
                        description="Core type system",
                        type="theory",
                        phase=1,
                        skill_ids=["typescript"],
                        duration_hours=8,
                        objectives=["Understand type annotations"],
                        resources=["https://typescriptlang.org"],
                    )
                ],
            )
        ],
    )


def _gap_analysis_payload() -> dict:
    return {
        "gapAnalysis": {
            "overallReadiness": 50,
            "summary": "Needs improvement",
            "gaps": [
                {
                    "skillId": "typescript",
                    "skillName": "TypeScript",
                    "currentLevel": 30,
                    "targetLevel": 80,
                    "gap": 50,
                    "priority": "high",
                    "recommendation": "Study generics",
                }
            ],
        }
    }


class TestLearningPlanRoute:
    @pytest.mark.asyncio
    async def test_no_gap_analysis_returns_422(self):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/learning-plan",
                json={},
            )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_gaps_returns_400(self):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/learning-plan",
                json={
                    "gapAnalysis": {
                        "overallReadiness": 50,
                        "summary": "No gaps",
                        "gaps": [],
                    }
                },
            )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_success_returns_plan(self):
        with patch(
            "app.routes.learning_plan.ainvoke_structured",
            new_callable=AsyncMock,
            return_value=_valid_plan_output(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/learning-plan", json=_gap_analysis_payload())

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TypeScript Mastery Plan"
        assert len(data["phases"]) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_500(self):
        with patch(
            "app.routes.learning_plan.ainvoke_structured",
            new_callable=AsyncMock,
            side_effect=Exception("LLM call failed"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/learning-plan", json=_gap_analysis_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_response_camel_case(self):
        with patch(
            "app.routes.learning_plan.ainvoke_structured",
            new_callable=AsyncMock,
            return_value=_valid_plan_output(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/learning-plan", json=_gap_analysis_payload())

        data = response.json()
        assert "totalHours" in data
        assert "totalWeeks" in data
        assert "skillIds" in data["phases"][0]["modules"][0]
        assert "durationHours" in data["phases"][0]["modules"][0]

    @pytest.mark.asyncio
    async def test_ainvoke_structured_called_with_correct_schema(self):
        mock_ainvoke = AsyncMock(return_value=_valid_plan_output())
        with patch("app.routes.learning_plan.ainvoke_structured", mock_ainvoke):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                await client.post("/api/learning-plan", json=_gap_analysis_payload())

        mock_ainvoke.assert_called_once()
        call_args = mock_ainvoke.call_args
        assert call_args[0][0] is LearningPlanOutput
        assert call_args[1]["agent_name"] == "learning_plan"
