"""Tests for the gap analysis route."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.schemas import GapAnalysisItemOutput, GapAnalysisOutput
from tests.conftest import _test_app


def _valid_gap_output() -> GapAnalysisOutput:
    return GapAnalysisOutput(
        overall_readiness=65,
        summary="Moderate readiness with key gaps in TypeScript",
        gaps=[
            GapAnalysisItemOutput(
                skill_id="typescript",
                skill_name="TypeScript",
                current_level=40,
                target_level=80,
                gap=40,
                priority="high",
                recommendation="Focus on generics and advanced types",
            )
        ],
    )


def _scores_payload() -> dict:
    return {
        "proficiencyScores": [
            {
                "skillId": "typescript",
                "skillName": "TypeScript",
                "score": 40,
                "confidence": 0.8,
                "reasoning": "Partial understanding",
            }
        ]
    }


class TestGapAnalysisRoute:
    @pytest.mark.asyncio
    async def test_empty_scores_returns_400(self):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.post("/api/gap-analysis", json={"proficiencyScores": []})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_success_returns_gap_analysis(self):
        with patch(
            "app.routes.gap_analysis.ainvoke_structured",
            new_callable=AsyncMock,
            return_value=_valid_gap_output(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        assert response.status_code == 200
        data = response.json()
        assert data["overallReadiness"] == 65
        assert len(data["gaps"]) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_500(self):
        with patch(
            "app.routes.gap_analysis.ainvoke_structured",
            new_callable=AsyncMock,
            side_effect=Exception("LLM call failed"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_response_camel_case(self):
        with patch(
            "app.routes.gap_analysis.ainvoke_structured",
            new_callable=AsyncMock,
            return_value=_valid_gap_output(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        data = response.json()
        assert "overallReadiness" in data
        assert "skillId" in data["gaps"][0]
        assert "currentLevel" in data["gaps"][0]
        assert "targetLevel" in data["gaps"][0]

    @pytest.mark.asyncio
    async def test_ainvoke_structured_called_with_correct_schema(self):
        mock_ainvoke = AsyncMock(return_value=_valid_gap_output())
        with patch("app.routes.gap_analysis.ainvoke_structured", mock_ainvoke):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                await client.post("/api/gap-analysis", json=_scores_payload())

        mock_ainvoke.assert_called_once()
        call_args = mock_ainvoke.call_args
        assert call_args[0][0] is GapAnalysisOutput
        assert call_args[1]["agent_name"] == "gap_analysis"
