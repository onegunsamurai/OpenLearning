from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from anthropic import APIStatusError, APITimeoutError, RateLimitError
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger("openlearning.llm")


def get_chat_model() -> ChatAnthropic:
    settings = get_settings()
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        anthropic_api_key=settings.anthropic_api_key,
    )


def parse_json_response(text: str) -> dict:
    """Parse JSON from AI response, stripping markdown code fences if present.

    Used by non-assessment routes (gap_analysis, parse_jd, learning_plan).
    Assessment pipeline agents use ainvoke_structured() instead.
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def _log_retry(retry_state: Any) -> None:
    """Log each retry attempt with structured context."""
    exc = retry_state.outcome.exception()
    agent_name = retry_state.kwargs.get("agent_name", "unknown")
    attempt = retry_state.attempt_number
    logger.warning(
        "LLM call retry",
        extra={
            "agent_name": agent_name,
            "attempt": attempt,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        },
    )


def get_structured_model(
    schema: type[BaseModel],
    *,
    agent_name: str = "unknown",
    max_retries: int = 3,
) -> Runnable:
    """Return a model that outputs validated Pydantic objects with retry.

    Chains: ChatAnthropic -> with_structured_output(schema) -> with_retry(...)
    """
    model = get_chat_model().with_structured_output(schema)

    return model.with_retry(
        retry_if_exception_type=(APITimeoutError, RateLimitError, APIStatusError),
        wait_exponential_jitter=True,
        stop_after_attempt=max_retries,
        before_sleep=_log_retry,
    )


async def ainvoke_structured(
    schema: type[BaseModel],
    prompt: str,
    *,
    agent_name: str = "unknown",
    max_retries: int = 3,
) -> BaseModel:
    """Invoke the LLM with structured output, retry, and logging.

    This is the primary entry point for all agent LLM calls. It handles:
    - Structured output validation via Pydantic schema
    - Retry with exponential backoff for transient failures
    - Structured logging for all calls (success and failure)
    """
    model = get_structured_model(schema, agent_name=agent_name, max_retries=max_retries)

    start = time.monotonic()
    try:
        result = await model.ainvoke(prompt)
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "LLM call succeeded",
            extra={
                "agent_name": agent_name,
                "duration_ms": duration_ms,
                "schema": schema.__name__,
            },
        )
        return result
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "LLM call failed",
            extra={
                "agent_name": agent_name,
                "duration_ms": duration_ms,
                "schema": schema.__name__,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        raise
