"""Domain exceptions for the assessment service layer.

These exceptions are raised by service functions and translated to HTTP
responses by FastAPI exception handlers registered in ``main.py``.
"""

from __future__ import annotations


class AssessmentError(Exception):
    """Base for all assessment domain errors."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class SessionTimedOutError(AssessmentError):
    """Session has expired (maps to HTTP 410)."""


class SessionAlreadyCompletedError(AssessmentError):
    """Session is already in completed state (maps to HTTP 409)."""


class AssessmentValidationError(AssessmentError):
    """Invalid input for an assessment operation (maps to HTTP 400)."""


class AssessmentNotCompleteError(AssessmentError):
    """Assessment pipeline hasn't finished yet (maps to HTTP 400)."""


class GraphInterruptError(AssessmentError):
    """Graph did not produce expected interrupt data (maps to HTTP 500)."""
