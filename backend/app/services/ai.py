from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar, Token

from anthropic import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

# OverloadedError (HTTP 529) is not yet re-exported from the public anthropic namespace.
# The SDK creates this class internally for 529 responses; the private import is stable
# across versions with the anthropic dependency pinned in requirements.txt.
from anthropic._exceptions import OverloadedError
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
        retry_if_exception_type=(
            APITimeoutError,
            RateLimitError,
            InternalServerError,
            OverloadedError,
        ),
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


def classify_anthropic_error(exc: Exception) -> tuple[int, str, dict[str, str]] | None:
    """Map an Anthropic SDK exception to (status_code, user_message, headers).

    Returns None if the exception is not a recognised Anthropic error.
    """
    if isinstance(exc, AuthenticationError):
        return (
            401,
            "Your API key is invalid or has been revoked. Please update it in settings.",
            {},
        )
    if isinstance(exc, RateLimitError):
        retry_after = getattr(getattr(exc, "response", None), "headers", {}).get(
            "retry-after", "30"
        )
        return (
            429,
            "Rate limit reached. Please wait a moment and try again.",
            {"Retry-After": retry_after},
        )
    if isinstance(exc, APITimeoutError):
        return (504, "The AI service timed out. Please try again.", {})
    if isinstance(exc, APIConnectionError):
        return (502, "Unable to reach the AI service. Please try again shortly.", {})
    if isinstance(exc, InternalServerError):
        return (502, "The AI service encountered an error. Please try again.", {})
    if isinstance(exc, OverloadedError):
        retry_after = getattr(getattr(exc, "response", None), "headers", {}).get(
            "retry-after", "30"
        )
        return (
            503,
            "The AI service is currently overloaded. Please try again in a moment.",
            {"Retry-After": retry_after},
        )
    return None
