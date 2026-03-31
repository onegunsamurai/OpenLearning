"""Typed domain events for assessment SSE streaming.

The service layer yields these events; the SSEAdapter translates them
to wire-format SSE strings.  The service has zero knowledge of SSE.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.assessment import ProficiencyScore


@dataclass(frozen=True, slots=True)
class QuestionEvent:
    """A new question is ready for the user."""

    text: str
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CompleteEvent:
    """The assessment pipeline has finished."""

    scores: list[ProficiencyScore] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    """An error occurred during graph execution."""

    status: int
    detail: str
    retry_after: str | None = None


AssessmentEvent = QuestionEvent | CompleteEvent | ErrorEvent
