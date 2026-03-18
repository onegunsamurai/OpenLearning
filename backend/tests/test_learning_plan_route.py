"""Tests for the learning plan route."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from tests.conftest import _test_app


def _valid_plan_response() -> str:
    return json.dumps(
        {
            "title": "TypeScript Mastery Plan",
            "summary": "A focused plan for TypeScript improvement",
            "totalHours": 30,
            "totalWeeks": 4,
            "phases": [
                {
                    "phase": 1,
                    "name": "Foundations",
                    "description": "Build core TypeScript skills",
                    "modules": [
                        {
                            "id": "mod-1",
                            "title": "TypeScript Basics",
                            "description": "Core type system",
                            "type": "theory",
                            "phase": 1,
                            "skillIds": ["typescript"],
                            "durationHours": 8,
                            "objectives": ["Understand type annotations"],
                            "resources": ["https://typescriptlang.org"],
                        }
                    ],
                }
            ],
        }
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
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = _valid_plan_response()
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.learning_plan.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/learning-plan", json=_gap_analysis_payload())

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "TypeScript Mastery Plan"
        assert len(data["phases"]) == 1

    @pytest.mark.asyncio
    async def test_llm_malformed_json_returns_500(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "not json"
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.learning_plan.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/learning-plan", json=_gap_analysis_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_llm_missing_phases_returns_500(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = json.dumps({"title": "Plan", "summary": "No phases"})
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.learning_plan.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/learning-plan", json=_gap_analysis_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_llm_missing_title_returns_500(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = json.dumps({"phases": [], "summary": "No title"})
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.learning_plan.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/learning-plan", json=_gap_analysis_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_llm_non_string_content_returns_500(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = ["not", "a", "string"]
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.learning_plan.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/learning-plan", json=_gap_analysis_payload())

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_response_camel_case(self):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = _valid_plan_response()
        mock_model.ainvoke.return_value = mock_response

        with patch("app.routes.learning_plan.get_chat_model", return_value=mock_model):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post("/api/learning-plan", json=_gap_analysis_payload())

        data = response.json()
        assert "totalHours" in data
        assert "totalWeeks" in data
        assert "skillIds" in data["phases"][0]["modules"][0]
        assert "durationHours" in data["phases"][0]["modules"][0]
