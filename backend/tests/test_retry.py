"""Tests for retry behavior in the LLM service layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic import APITimeoutError, AuthenticationError, InternalServerError, RateLimitError

from app.agents.schemas import EvaluationOutput
from app.services.ai import ainvoke_structured, get_structured_model


def _make_mock_chain(side_effects):
    """Create a mock that simulates get_chat_model().with_structured_output().with_retry().

    The mock chain must use MagicMock (not AsyncMock) for sync methods
    and AsyncMock for ainvoke.
    """
    mock_runnable = MagicMock()
    mock_runnable.ainvoke = AsyncMock(side_effect=side_effects)
    mock_runnable.with_retry = MagicMock(return_value=mock_runnable)

    mock_structured = MagicMock()
    mock_structured.with_structured_output = MagicMock(return_value=mock_runnable)

    return mock_structured, mock_runnable


class TestRetryConfiguration:
    def test_configures_retry_with_transient_error_types(self):
        """with_retry should be called with APITimeoutError, RateLimitError, and InternalServerError."""
        mock_chat, mock_runnable = _make_mock_chain([])

        with patch("app.services.ai.get_chat_model", return_value=mock_chat):
            get_structured_model(EvaluationOutput, agent_name="test")

        mock_runnable.with_retry.assert_called_once()
        call_kwargs = mock_runnable.with_retry.call_args[1]
        assert APITimeoutError in call_kwargs["retry_if_exception_type"]
        assert RateLimitError in call_kwargs["retry_if_exception_type"]
        assert InternalServerError in call_kwargs["retry_if_exception_type"]

    def test_configures_retry_with_max_attempts(self):
        """with_retry should respect the max_retries parameter."""
        mock_chat, mock_runnable = _make_mock_chain([])

        with patch("app.services.ai.get_chat_model", return_value=mock_chat):
            get_structured_model(EvaluationOutput, agent_name="test", max_retries=5)

        call_kwargs = mock_runnable.with_retry.call_args[1]
        assert call_kwargs["stop_after_attempt"] == 5

    def test_configures_exponential_jitter(self):
        """with_retry should use exponential backoff with jitter."""
        mock_chat, mock_runnable = _make_mock_chain([])

        with patch("app.services.ai.get_chat_model", return_value=mock_chat):
            get_structured_model(EvaluationOutput, agent_name="test")

        call_kwargs = mock_runnable.with_retry.call_args[1]
        assert call_kwargs["wait_exponential_jitter"] is True

    def test_configures_structured_output_with_schema(self):
        """with_structured_output should receive the Pydantic schema."""
        mock_chat, _ = _make_mock_chain([])

        with patch("app.services.ai.get_chat_model", return_value=mock_chat):
            get_structured_model(EvaluationOutput, agent_name="test")

        mock_chat.with_structured_output.assert_called_once_with(EvaluationOutput)


class TestAinvokeStructured:
    @pytest.mark.asyncio
    async def test_returns_validated_output(self):
        """Should return the validated Pydantic model from the LLM."""
        success_output = EvaluationOutput(
            confidence=0.8, bloom_level="apply", evidence=["Good"], reasoning="OK"
        )

        mock_chat, _ = _make_mock_chain([success_output])

        with patch("app.services.ai.get_chat_model", return_value=mock_chat):
            result = await ainvoke_structured(EvaluationOutput, "test prompt", agent_name="test")

        assert result.confidence == 0.8
        assert result.bloom_level == "apply"

    @pytest.mark.asyncio
    async def test_fails_fast_on_auth_error(self):
        """Should NOT retry on AuthenticationError — fail immediately."""
        mock_chat, mock_runnable = _make_mock_chain(
            AuthenticationError(
                message="Invalid API key",
                response=MagicMock(status_code=401, headers={}),
                body=None,
            )
        )

        with (
            patch("app.services.ai.get_chat_model", return_value=mock_chat),
            pytest.raises(AuthenticationError),
        ):
            await ainvoke_structured(EvaluationOutput, "test prompt", agent_name="test")

        assert mock_runnable.ainvoke.call_count == 1

    @pytest.mark.asyncio
    async def test_propagates_timeout_after_all_retries(self):
        """Should raise APITimeoutError after retries are exhausted."""
        mock_chat, _ = _make_mock_chain(APITimeoutError(request=None))

        with (
            patch("app.services.ai.get_chat_model", return_value=mock_chat),
            pytest.raises(APITimeoutError),
        ):
            await ainvoke_structured(EvaluationOutput, "test prompt", agent_name="test")

    @pytest.mark.asyncio
    async def test_logs_on_success(self, caplog):
        """Should log a success message with duration and schema name."""
        import logging

        success_output = EvaluationOutput(
            confidence=0.9, bloom_level="create", evidence=["Excellent"], reasoning="Great"
        )

        mock_chat, _ = _make_mock_chain([success_output])

        with (
            patch("app.services.ai.get_chat_model", return_value=mock_chat),
            caplog.at_level(logging.INFO, logger="openlearning.llm"),
        ):
            await ainvoke_structured(EvaluationOutput, "test prompt", agent_name="test_agent")

        assert any("LLM call succeeded" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_logs_on_failure(self, caplog):
        """Should log an error message when LLM call fails."""
        import logging

        mock_chat, _ = _make_mock_chain(
            AuthenticationError(
                message="bad key",
                response=MagicMock(status_code=401, headers={}),
                body=None,
            )
        )

        with (
            patch("app.services.ai.get_chat_model", return_value=mock_chat),
            caplog.at_level(logging.ERROR, logger="openlearning.llm"),
            pytest.raises(AuthenticationError),
        ):
            await ainvoke_structured(EvaluationOutput, "test prompt", agent_name="test_agent")

        assert any("LLM call failed" in r.message for r in caplog.records)
