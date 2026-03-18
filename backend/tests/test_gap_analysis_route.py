"""Tests for the gap analysis route."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import _test_app


def _valid_gap_response() -> str:
    return json.dumps(
        {
            "overallReadiness": 65,
            "summary": "Moderate readiness with key gaps in TypeScript",
            "gaps": [
                {
                    "skillId": "typescript",
                    "skillName": "TypeScript",
                    "currentLevel": 40,
                    "targetLevel": 80,
                    "gap": 40,
                    "priority": "high",
                    "recommendation": "Focus on generics and advanced types",
                }
            ],
        }
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
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = _valid_gap_response()
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.gap_analysis.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        assert response.status_code == 200
        data = response.json()
        assert data["overallReadiness"] == 65
        assert len(data["gaps"]) == 1

    @pytest.mark.asyncio
    async def test_llm_malformed_json_returns_500(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "This is not JSON at all"
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.gap_analysis.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_llm_missing_overall_readiness_returns_500(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = json.dumps({"summary": "No readiness", "gaps": []})
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.gap_analysis.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_llm_non_numeric_readiness_returns_500(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = json.dumps(
            {"overallReadiness": "high", "summary": "Bad", "gaps": []}
        )
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.gap_analysis.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_llm_gaps_not_list_returns_500(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = json.dumps({"overallReadiness": 50, "summary": "Bad", "gaps": {}})
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.gap_analysis.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_llm_non_string_content_returns_500(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = ["not", "a", "string"]
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.gap_analysis.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_response_camel_case(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = _valid_gap_response()
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.gap_analysis.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/gap-analysis", json=_scores_payload())

        data = response.json()
        assert "overallReadiness" in data
        assert "skillId" in data["gaps"][0]
        assert "currentLevel" in data["gaps"][0]
        assert "targetLevel" in data["gaps"][0]
