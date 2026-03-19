from __future__ import annotations

import json
import logging
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar, Token

from anthropic import APITimeoutError, InternalServerError, RateLimitError
from langchain_anthropic import ChatAnthropic
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger("openlearning.llm")

_current_api_key: ContextVar[str | None] = ContextVar("_current_api_key", default=None)


def set_current_api_key(key: str) -> Token[str | None]:
    """Set the per-request API key in the current context. Returns a token for reset."""
    return _current_api_key.set(key)


def reset_current_api_key(token: Token[str | None]) -> None:
    """Reset the contextvar to its previous value."""
    _current_api_key.reset(token)


@contextmanager
def api_key_scope(key: str):
    """Context manager to set and reset the per-request API key."""
    token = _current_api_key.set(key)
    try:
        yield
    finally:
        _current_api_key.reset(token)


def get_chat_model(api_key: str | None = None) -> ChatAnthropic:
    key = api_key or _current_api_key.get() or get_settings().anthropic_api_key
    if not key:
        raise ValueError("No API key available")
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0,
        anthropic_api_key=key,
    )


def parse_json_response(text: str) -> dict:
    """Parse JSON from AI response, stripping markdown code fences if present.

    Used by non-assessment routes (gap_analysis, learning_plan).
    Assessment pipeline agents use ainvoke_structured() instead.
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


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
        retry_if_exception_type=(APITimeoutError, RateLimitError, InternalServerError),
        wait_exponential_jitter=True,
        stop_after_attempt=max_retries,
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
