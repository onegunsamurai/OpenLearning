"""Tests for the plan-generator prompt update introduced by issue #177.

AC-14: prompt instructs the LLM to set url=null for type=video resources while
preserving the existing resource-type mix instruction.
"""

from __future__ import annotations

from app.prompts.plan_generator import PLAN_GEN_PROMPT


class TestPlanGenPrompt:
    def test_video_url_null_instruction_present(self):
        """AC-14: prompt must instruct the LLM to emit url=null for videos."""
        prompt_lower = PLAN_GEN_PROMPT.lower()
        assert "video" in prompt_lower
        assert "url to null" in prompt_lower

    def test_resource_type_mix_preserved(self):
        """Pre-existing instruction to mix resource types must remain — the
        new node only enriches videos; article/project/exercise still ship
        with LLM-emitted URLs."""
        for kind in ("video", "article", "project", "exercise"):
            assert kind in PLAN_GEN_PROMPT.lower(), f"resource type {kind!r} missing"

    def test_template_format_args_unchanged(self):
        """No new format placeholders introduced — existing callers must
        still be able to format the prompt with the legacy three args."""
        rendered = PLAN_GEN_PROMPT.format(
            target_level="mid",
            domain="backend_engineering",
            gap_summary="- HTTP fundamentals\n- REST API design",
        )
        assert "mid" in rendered
        assert "backend_engineering" in rendered
        assert "HTTP fundamentals" in rendered
