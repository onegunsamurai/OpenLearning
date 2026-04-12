"""Tests for the plan_generator agent producing nested concept shapes.

Issue #168: each LLM-emitted concept must map to a ConceptItem carrying its
own resources; the LearningPhase must NOT expose a phase-level resources
field.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.plan_generator import generate_plan
from app.agents.schemas import (
    PlanConceptOutput,
    PlanOutput,
    PlanPhaseOutput,
    PlanResourceOutput,
)
from app.graph.state import BloomLevel, KnowledgeNode, LearningPhase, slugify_concept


class TestSlugifyConcept:
    def test_basic_lowercasing_and_dashing(self):
        assert slugify_concept("Server Actions") == "server-actions"

    def test_collapses_non_alphanumeric(self):
        assert slugify_concept("Async I/O & Streams") == "async-i-o-streams"

    def test_trims_leading_and_trailing_dashes(self):
        assert slugify_concept("  React  ") == "react"
        assert slugify_concept("!!Hooks!!") == "hooks"

    def test_empty_string_returns_empty(self):
        assert slugify_concept("") == ""


class TestGeneratePlanConceptShape:
    @pytest.mark.asyncio
    async def test_generate_plan_produces_nested_concepts(self):
        """generate_plan should map LLM PlanConceptOutput into ConceptItem
        carrying its own resources, and the resulting LearningPhase must not
        expose a phase-level `resources` attribute."""
        fake_llm_output = PlanOutput(
            summary="Learn async.",
            total_hours=20.0,
            phases=[
                PlanPhaseOutput(
                    phase_number=1,
                    title="Async Fundamentals",
                    rationale="Foundation first",
                    estimated_hours=10.0,
                    concepts=[
                        PlanConceptOutput(
                            name="Event loop",
                            description="How the loop schedules coroutines.",
                            resources=[
                                PlanResourceOutput(
                                    type="article",
                                    title="Event loop primer",
                                    url="https://example.com/el",
                                ),
                            ],
                        ),
                        PlanConceptOutput(
                            name="await & Futures",
                            description="Awaiting coroutines and futures.",
                            resources=[
                                PlanResourceOutput(
                                    type="project",
                                    title="Build an async fetcher",
                                    url=None,
                                ),
                                PlanResourceOutput(
                                    type="video",
                                    title="Futures explained",
                                    url="https://example.com/f",
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

        gap_nodes = [
            KnowledgeNode(
                concept="async_io",
                confidence=0.3,
                bloom_level=BloomLevel.apply,
                prerequisites=[],
                evidence=[],
            )
        ]

        with patch(
            "app.agents.plan_generator.ainvoke_structured",
            new=AsyncMock(return_value=fake_llm_output),
        ):
            result = await generate_plan(
                {"gap_nodes": gap_nodes, "target_level": "mid"}  # type: ignore[typeddict-item]
            )

        plan = result["learning_plan"]
        assert plan.total_hours == 20.0
        assert len(plan.phases) == 1

        phase: LearningPhase = plan.phases[0]
        # Phase must NOT expose a phase-level resources field any longer.
        assert not hasattr(phase, "resources")

        assert len(phase.concepts) == 2

        event_loop, await_futures = phase.concepts
        assert event_loop.key == "event-loop"
        assert event_loop.name == "Event loop"
        assert event_loop.description == "How the loop schedules coroutines."
        assert len(event_loop.resources) == 1
        assert event_loop.resources[0].title == "Event loop primer"

        assert await_futures.key == "await-futures"
        assert await_futures.name == "await & Futures"
        assert len(await_futures.resources) == 2
        assert {r.type for r in await_futures.resources} == {"project", "video"}

    @pytest.mark.asyncio
    async def test_generate_plan_empty_gap_nodes_returns_empty_plan(self):
        """No gaps → empty plan, no LLM call needed."""
        result = await generate_plan({"gap_nodes": []})  # type: ignore[typeddict-item]
        plan = result["learning_plan"]
        assert plan.phases == []
        assert plan.total_hours == 0
        assert "No significant gaps" in plan.summary
