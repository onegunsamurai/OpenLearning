"""Tests for global Anthropic error handling."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.services.ai import classify_anthropic_error
from tests.conftest import _test_app, _TestSessionFactory, seed_session


def _make_httpx_response(status_code: int, headers: dict | None = None) -> httpx.Response:
    """Build a minimal httpx.Response with a bound request."""
    resp = httpx.Response(
        status_code=status_code,
        headers=headers or {},
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )
    return resp


def _make_auth_error():
    """Create a realistic AuthenticationError."""
    from anthropic import AuthenticationError

    return AuthenticationError(
        message="Invalid API key",
        response=_make_httpx_response(401),
        body={"error": {"message": "Invalid API key"}},
    )


def _make_rate_limit_error(retry_after: str = "45"):
    """Create a realistic RateLimitError with Retry-After header."""
    from anthropic import RateLimitError

    return RateLimitError(
        message="Rate limit exceeded",
        response=_make_httpx_response(429, {"retry-after": retry_after}),
        body={"error": {"message": "Rate limit exceeded"}},
    )


def _make_connection_error():
    """Create a realistic APIConnectionError."""
    from anthropic import APIConnectionError

    return APIConnectionError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )


def _make_timeout_error():
    """Create a realistic APITimeoutError."""
    from anthropic import APITimeoutError

    return APITimeoutError(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))


def _make_internal_server_error():
    """Create a realistic InternalServerError."""
    from anthropic import InternalServerError

    return InternalServerError(
        message="Internal server error",
        response=_make_httpx_response(500),
        body={"error": {"message": "Internal server error"}},
    )


class TestGapAnalysisAnthropicErrors:
    """Test that Anthropic errors in gap-analysis route are handled globally."""

    @pytest.mark.asyncio
    async def test_authentication_error_returns_401(self, setup_db):
        with patch(
            "app.routes.gap_analysis.ainvoke_structured",
            new_callable=AsyncMock,
            side_effect=_make_auth_error(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/gap-analysis",
                    json={
                        "proficiencyScores": [
                            {
                                "skillId": "react",
                                "skillName": "React",
                                "score": 70,
                                "confidence": 0.8,
                                "reasoning": "ok",
                            }
                        ]
                    },
                )

        assert response.status_code == 401
        assert "API key" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rate_limit_error_returns_429_with_retry_after(self, setup_db):
        with patch(
            "app.routes.gap_analysis.ainvoke_structured",
            new_callable=AsyncMock,
            side_effect=_make_rate_limit_error("45"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/gap-analysis",
                    json={
                        "proficiencyScores": [
                            {
                                "skillId": "react",
                                "skillName": "React",
                                "score": 70,
                                "confidence": 0.8,
                                "reasoning": "ok",
                            }
                        ]
                    },
                )

        assert response.status_code == 429
        assert "Rate limit" in response.json()["detail"]
        assert response.headers.get("retry-after") == "45"

    @pytest.mark.asyncio
    async def test_connection_error_returns_502(self, setup_db):
        with patch(
            "app.routes.gap_analysis.ainvoke_structured",
            new_callable=AsyncMock,
            side_effect=_make_connection_error(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/gap-analysis",
                    json={
                        "proficiencyScores": [
                            {
                                "skillId": "react",
                                "skillName": "React",
                                "score": 70,
                                "confidence": 0.8,
                                "reasoning": "ok",
                            }
                        ]
                    },
                )

        assert response.status_code == 502
        assert "Unable to reach" in response.json()["detail"]


class TestLearningPlanAnthropicErrors:
    """Test that Anthropic errors in learning-plan route are handled globally."""

    @pytest.mark.asyncio
    async def test_authentication_error_returns_401(self, setup_db):
        with patch(
            "app.routes.learning_plan.ainvoke_structured",
            new_callable=AsyncMock,
            side_effect=_make_auth_error(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/learning-plan",
                    json={
                        "gapAnalysis": {
                            "overallReadiness": 50,
                            "summary": "Needs work",
                            "gaps": [
                                {
                                    "skillId": "ts",
                                    "skillName": "TypeScript",
                                    "currentLevel": 30,
                                    "targetLevel": 80,
                                    "gap": 50,
                                    "priority": "high",
                                    "recommendation": "Study",
                                }
                            ],
                        }
                    },
                )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_timeout_error_returns_504(self, setup_db):
        with patch(
            "app.routes.learning_plan.ainvoke_structured",
            new_callable=AsyncMock,
            side_effect=_make_timeout_error(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/learning-plan",
                    json={
                        "gapAnalysis": {
                            "overallReadiness": 50,
                            "summary": "Needs work",
                            "gaps": [
                                {
                                    "skillId": "ts",
                                    "skillName": "TypeScript",
                                    "currentLevel": 30,
                                    "targetLevel": 80,
                                    "gap": 50,
                                    "priority": "high",
                                    "recommendation": "Study",
                                }
                            ],
                        }
                    },
                )

        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_internal_server_error_returns_502(self, setup_db):
        with patch(
            "app.routes.learning_plan.ainvoke_structured",
            new_callable=AsyncMock,
            side_effect=_make_internal_server_error(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/learning-plan",
                    json={
                        "gapAnalysis": {
                            "overallReadiness": 50,
                            "summary": "Needs work",
                            "gaps": [
                                {
                                    "skillId": "ts",
                                    "skillName": "TypeScript",
                                    "currentLevel": 30,
                                    "targetLevel": 80,
                                    "gap": 50,
                                    "priority": "high",
                                    "recommendation": "Study",
                                }
                            ],
                        }
                    },
                )

        assert response.status_code == 502
        assert "encountered an error" in response.json()["detail"]


class TestAssessmentSSEAnthropicErrors:
    """Test that Anthropic errors in SSE stream produce structured [ERROR] events."""

    @pytest.mark.asyncio
    async def test_auth_error_in_sse_stream(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        from tests.conftest import _mock_graph

        _mock_graph.ainvoke = AsyncMock(side_effect=_make_auth_error())

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/sess-001/respond", json={"response": "answer"}
                )

            body = response.text
            assert "[ERROR]" in body

            # Extract and parse the error JSON
            for line in body.split("\n"):
                if "[ERROR]" in line:
                    error_json = line.split("[ERROR]")[1].strip()
                    parsed = json.loads(error_json)
                    assert parsed["status"] == 401
                    assert "API key" in parsed["detail"]
                    break
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_rate_limit_error_in_sse_stream(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        from tests.conftest import _mock_graph

        _mock_graph.ainvoke = AsyncMock(side_effect=_make_rate_limit_error("60"))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/sess-001/respond", json={"response": "answer"}
                )

            body = response.text
            for line in body.split("\n"):
                if "[ERROR]" in line:
                    error_json = line.split("[ERROR]")[1].strip()
                    parsed = json.loads(error_json)
                    assert parsed["status"] == 429
                    assert parsed["retryAfter"] == "60"
                    break
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_generic_error_in_sse_stream(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        from tests.conftest import _mock_graph

        _mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("unexpected"))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/sess-001/respond", json={"response": "answer"}
                )

            body = response.text
            for line in body.split("\n"):
                if "[ERROR]" in line:
                    error_json = line.split("[ERROR]")[1].strip()
                    parsed = json.loads(error_json)
                    assert parsed["status"] == 500
                    assert parsed["detail"] == "An internal error occurred"
                    break
        finally:
            _mock_graph.reset_mock()


class TestClassifyAnthropicError:
    """Direct unit tests for classify_anthropic_error."""

    def test_authentication_error(self) -> None:
        exc = _make_auth_error()
        result = classify_anthropic_error(exc)
        assert result is not None
        status, detail, headers = result
        assert status == 401
        assert "API key" in detail
        assert headers == {}

    def test_rate_limit_error_with_retry_after(self) -> None:
        exc = _make_rate_limit_error("45")
        result = classify_anthropic_error(exc)
        assert result is not None
        status, detail, headers = result
        assert status == 429
        assert "Rate limit" in detail
        assert headers["Retry-After"] == "45"

    def test_rate_limit_error_default_retry_after(self) -> None:
        """RateLimitError without retry-after header defaults to '30'."""
        from anthropic import RateLimitError

        exc = RateLimitError(
            message="Rate limit exceeded",
            response=_make_httpx_response(429),
            body={"error": {"message": "Rate limit exceeded"}},
        )
        result = classify_anthropic_error(exc)
        assert result is not None
        _, _, headers = result
        assert headers["Retry-After"] == "30"

    def test_timeout_error(self) -> None:
        exc = _make_timeout_error()
        result = classify_anthropic_error(exc)
        assert result is not None
        status, detail, headers = result
        assert status == 504
        assert "timed out" in detail
        assert headers == {}

    def test_connection_error(self) -> None:
        exc = _make_connection_error()
        result = classify_anthropic_error(exc)
        assert result is not None
        status, detail, headers = result
        assert status == 502
        assert "Unable to reach" in detail
        assert headers == {}

    def test_internal_server_error(self) -> None:
        exc = _make_internal_server_error()
        result = classify_anthropic_error(exc)
        assert result is not None
        status, detail, headers = result
        assert status == 502
        assert "encountered an error" in detail
        assert headers == {}

    def test_unrecognised_exception_returns_none(self) -> None:
        result = classify_anthropic_error(ValueError("something else"))
        assert result is None

    def test_generic_runtime_error_returns_none(self) -> None:
        result = classify_anthropic_error(RuntimeError("unexpected"))
        assert result is None
