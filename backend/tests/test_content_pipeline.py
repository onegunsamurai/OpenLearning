from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.schemas import BloomValidatorOutput, ContentGeneratorOutput, ContentSectionOutput
from app.graph.content_pipeline import build_content_graph


class TestContentPipelineGraph:
    """Test the content pipeline graph structure."""

    def test_graph_builds_successfully(self) -> None:
        graph = build_content_graph()
        assert graph is not None

    def test_graph_has_all_nodes(self) -> None:
        graph = build_content_graph()
        node_names = set(graph.nodes.keys())
        expected = {
            "input_reader",
            "gap_prioritizer",
            "objective_generator",
            "generate_all_content",
            "validate_all_content",
        }
        assert expected.issubset(node_names)


class TestContentPipelineIntegration:
    """Integration tests that run the full pipeline with mocked LLM calls."""

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.get_db")
    @patch("app.agents.content_nodes._persist_materials")
    @patch("app.agents.content_nodes.ainvoke_structured")
    async def test_full_pipeline_happy_path(
        self,
        mock_ainvoke: AsyncMock,
        mock_persist: AsyncMock,
        mock_get_db: AsyncMock,
        setup_db,
    ) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from tests.conftest import _override_get_db, _TestSessionFactory, seed_result, seed_session

        mock_get_db.side_effect = _override_get_db

        # Seed test data
        async with _TestSessionFactory() as db:
            await seed_session(db, "sess-pipe", "thread-pipe", "completed")
            await seed_result(
                db,
                "sess-pipe",
                gap_nodes=[
                    {
                        "concept": "http_fundamentals",
                        "confidence": 0.3,
                        "bloom_level": "remember",
                        "prerequisites": [],
                        "evidence": ["Partial understanding"],
                    },
                ],
            )

        # Mock LLM: first call is content generation, second is validation
        content_output = ContentGeneratorOutput(
            sections=[
                ContentSectionOutput(
                    type="explanation",
                    title="Understanding HTTP",
                    body="HTTP is a protocol for web communication...",
                ),
                ContentSectionOutput(
                    type="quiz",
                    title="HTTP Quiz",
                    body="What is HTTP?",
                    answer="HyperText Transfer Protocol",
                ),
            ]
        )
        validator_output = BloomValidatorOutput(
            bloom_alignment=0.9,
            accuracy=0.95,
            clarity=0.9,
            evidence_alignment=0.85,
            critique="",
        )

        # ainvoke_structured is called twice per gap: once for generation, once for validation
        mock_ainvoke.side_effect = [content_output, validator_output]

        # Build and run graph
        from app.graph.content_pipeline import compile_content_graph

        checkpointer = MemorySaver()
        graph = compile_content_graph(checkpointer)

        config = {"configurable": {"thread_id": "test-content-pipe"}}
        initial_state = {"session_id": "sess-pipe", "domain": "backend_engineering"}

        result = await graph.ainvoke(initial_state, config)

        assert "final_materials" in result
        assert "http_fundamentals" in result["final_materials"]
        mat = result["final_materials"]["http_fundamentals"]
        assert mat.bloom_score >= 0.75
        assert mat.quality_score >= 0.70
        assert mat.iteration_count == 1
        assert mat.quality_flag is None

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.get_db")
    @patch("app.agents.content_nodes._persist_materials")
    @patch("app.agents.content_nodes.ainvoke_structured")
    async def test_pipeline_with_retry(
        self,
        mock_ainvoke: AsyncMock,
        mock_persist: AsyncMock,
        mock_get_db: AsyncMock,
        setup_db,
    ) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        from tests.conftest import _override_get_db, _TestSessionFactory, seed_result, seed_session

        mock_get_db.side_effect = _override_get_db

        async with _TestSessionFactory() as db:
            await seed_session(db, "sess-retry", "thread-retry", "completed")
            await seed_result(
                db,
                "sess-retry",
                gap_nodes=[
                    {
                        "concept": "http_fundamentals",
                        "confidence": 0.3,
                        "bloom_level": "remember",
                        "prerequisites": [],
                        "evidence": ["Partial understanding"],
                    },
                ],
            )

        content_output = ContentGeneratorOutput(
            sections=[
                ContentSectionOutput(type="explanation", title="HTTP", body="HTTP explanation..."),
            ]
        )
        failing_validation = BloomValidatorOutput(
            bloom_alignment=0.4,
            accuracy=0.5,
            clarity=0.5,
            evidence_alignment=0.5,
            critique="Needs more depth at Understand level.",
        )
        passing_validation = BloomValidatorOutput(
            bloom_alignment=0.9,
            accuracy=0.9,
            clarity=0.9,
            evidence_alignment=0.9,
            critique="",
        )

        # Call sequence: generate, validate(fail), regenerate, validate(pass)
        mock_ainvoke.side_effect = [
            content_output,
            failing_validation,
            content_output,
            passing_validation,
        ]

        from app.graph.content_pipeline import compile_content_graph

        checkpointer = MemorySaver()
        graph = compile_content_graph(checkpointer)

        config = {"configurable": {"thread_id": "test-retry-pipe"}}
        initial_state = {"session_id": "sess-retry", "domain": "backend_engineering"}

        result = await graph.ainvoke(initial_state, config)

        mat = result["final_materials"]["http_fundamentals"]
        assert mat.iteration_count == 2
        assert mat.quality_flag is None
