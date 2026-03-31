"""Tests for SSEAdapter — domain event → SSE string translation."""

from __future__ import annotations

import json

import pytest

from app.models.assessment import ProficiencyScore
from app.models.events import CompleteEvent, ErrorEvent, QuestionEvent
from app.services.sse_adapter import SSEAdapter


async def _collect(events):
    """Consume an async generator of events through the SSEAdapter."""
    adapter = SSEAdapter()

    async def _gen():
        for e in events:
            yield e

    lines = []
    async for line in adapter.adapt(_gen()):
        lines.append(line)
    return lines


class TestQuestionEvent:
    @pytest.mark.asyncio
    async def test_yields_question_text(self):
        lines = await _collect([QuestionEvent(text="What is React?", meta={"type": "calibration"})])
        assert lines[0] == "data: What is React?\n\n"

    @pytest.mark.asyncio
    async def test_yields_meta_marker(self):
        meta = {"type": "calibration", "step": 1, "total_steps": 3}
        lines = await _collect([QuestionEvent(text="Q", meta=meta)])
        assert lines[1].startswith("data: [META]")
        parsed = json.loads(lines[1].removeprefix("data: [META]").strip())
        assert parsed["type"] == "calibration"
        assert parsed["step"] == 1

    @pytest.mark.asyncio
    async def test_yields_done_marker(self):
        lines = await _collect([QuestionEvent(text="Q", meta={})])
        assert lines[-1] == "data: [DONE]\n\n"

    @pytest.mark.asyncio
    async def test_empty_meta(self):
        lines = await _collect([QuestionEvent(text="Q", meta={})])
        meta_line = lines[1]
        parsed = json.loads(meta_line.removeprefix("data: [META]").strip())
        assert parsed == {}


class TestCompleteEvent:
    @pytest.mark.asyncio
    async def test_yields_assessment_complete_marker(self):
        lines = await _collect([CompleteEvent(scores=[])])
        assert lines[0] == "data: [ASSESSMENT_COMPLETE]\n\n"

    @pytest.mark.asyncio
    async def test_yields_scores_json(self):
        scores = [
            ProficiencyScore(
                skill_id="react",
                skill_name="React",
                score=85,
                confidence=0.85,
                reasoning="Good",
            )
        ]
        lines = await _collect([CompleteEvent(scores=scores)])
        # Second line contains JSON scores
        scores_line = lines[1]
        assert "```json" in scores_line
        json_part = scores_line.split("```json\n")[1].split("\n```")[0]
        parsed = json.loads(json_part)
        assert len(parsed["scores"]) == 1
        assert parsed["scores"][0]["skillId"] == "react"

    @pytest.mark.asyncio
    async def test_yields_done_marker(self):
        lines = await _collect([CompleteEvent(scores=[])])
        assert lines[-1] == "data: [DONE]\n\n"


class TestErrorEvent:
    @pytest.mark.asyncio
    async def test_yields_error_marker(self):
        lines = await _collect([ErrorEvent(status=500, detail="Internal error")])
        assert len(lines) == 1
        assert lines[0].startswith("data: [ERROR]")

    @pytest.mark.asyncio
    async def test_error_payload_structure(self):
        lines = await _collect([ErrorEvent(status=429, detail="Rate limited", retry_after="30")])
        payload = json.loads(lines[0].removeprefix("data: [ERROR]").strip())
        assert payload["status"] == 429
        assert payload["detail"] == "Rate limited"
        assert payload["retryAfter"] == "30"

    @pytest.mark.asyncio
    async def test_error_no_retry_after(self):
        lines = await _collect([ErrorEvent(status=500, detail="boom")])
        payload = json.loads(lines[0].removeprefix("data: [ERROR]").strip())
        assert payload["retryAfter"] is None


class TestMixedEvents:
    @pytest.mark.asyncio
    async def test_multiple_events_in_order(self):
        events = [
            QuestionEvent(text="Q1", meta={"step": 1}),
            QuestionEvent(text="Q2", meta={"step": 2}),
            CompleteEvent(scores=[]),
        ]
        lines = await _collect(events)
        # Q1: text + meta + done = 3 lines
        # Q2: text + meta + done = 3 lines
        # Complete: marker + scores + done = 3 lines
        assert len(lines) == 9
        assert "Q1" in lines[0]
        assert "Q2" in lines[3]
        assert "[ASSESSMENT_COMPLETE]" in lines[6]
