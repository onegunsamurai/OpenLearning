"""SSE adapter that translates typed domain events to wire-format strings.

This is the **only** place SSE formatting lives.  The service layer yields
domain events (``QuestionEvent``, ``CompleteEvent``, ``ErrorEvent``); this
adapter converts them to the ``data: …\n\n`` lines expected by the frontend.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterable, AsyncIterator

from app.models.events import AssessmentEvent, CompleteEvent, ErrorEvent, QuestionEvent


class SSEAdapter:
    """Translates an async stream of ``AssessmentEvent`` to SSE strings."""

    async def adapt(self, events: AsyncIterable[AssessmentEvent]) -> AsyncIterator[str]:
        async for event in events:
            match event:
                case QuestionEvent(text=text, meta=meta):
                    yield f"data: {text}\n\n"
                    yield f"data: [META]{json.dumps(meta)}\n\n"
                    yield "data: [DONE]\n\n"

                case CompleteEvent(scores=scores):
                    yield "data: [ASSESSMENT_COMPLETE]\n\n"
                    scores_json = json.dumps(
                        {"scores": [s.model_dump(by_alias=True) for s in scores]}
                    )
                    yield f"data: ```json\n{scores_json}\n```\n\n"
                    yield "data: [DONE]\n\n"

                case ErrorEvent(status=status, detail=detail, retry_after=retry_after):
                    error_payload = json.dumps(
                        {
                            "status": status,
                            "detail": detail,
                            "retryAfter": retry_after,
                        }
                    )
                    yield f"data: [ERROR]{error_payload}\n\n"
