"""Tests for individual agents with mocked LLM responses."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.knowledge_mapper import update_knowledge_graph
from app.agents.question_generator import generate_question
from app.agents.response_evaluator import evaluate_response
from app.agents.schemas import EvaluationOutput, QuestionOutput
from app.graph.state import make_initial_state
from app.models.assessment_pipeline import EvaluationResult, Question, Response
from app.models.bloom import BloomLevel
from app.models.knowledge import KnowledgeGraph, KnowledgeNode


class TestKnowledgeMapper:
    """Knowledge mapper is pure Python — no mocking needed."""

    def test_updates_existing_node(self):
        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["knowledge_graph"] = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="http_fundamentals",
                    confidence=0.5,
                    bloom_level=BloomLevel.understand,
                    evidence=["old evidence"],
                )
            ],
            edges=[],
        )
        state["question_history"] = [
            Question(
                id="q-1",
                topic="http_fundamentals",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
        ]
        state["latest_evaluation"] = EvaluationResult(
            question_id="q-1",
            confidence=0.9,
            bloom_level=BloomLevel.apply,
            evidence=["new evidence"],
        )

        result = update_knowledge_graph(state)
        kg = result["knowledge_graph"]
        node = kg.get_node("http_fundamentals")
        # 0.7 * 0.5 + 0.3 * 0.9 = 0.62
        assert abs(node.confidence - 0.62) < 0.01
        assert node.bloom_level == BloomLevel.apply  # upgraded
        assert "new evidence" in node.evidence

    def test_inserts_new_node(self):
        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["question_history"] = [
            Question(
                id="q-1",
                topic="new_concept",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
        ]
        state["latest_evaluation"] = EvaluationResult(
            question_id="q-1",
            confidence=0.6,
            bloom_level=BloomLevel.understand,
            evidence=["some evidence"],
        )

        result = update_knowledge_graph(state)
        kg = result["knowledge_graph"]
        assert kg.get_node("new_concept") is not None
        assert kg.get_node("new_concept").confidence == 0.6

    def test_tracks_topics_evaluated(self):
        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["topics_evaluated"] = ["existing_topic"]
        state["question_history"] = [
            Question(
                id="q-1",
                topic="new_topic",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
        ]
        state["latest_evaluation"] = EvaluationResult(
            question_id="q-1",
            confidence=0.5,
            bloom_level=BloomLevel.understand,
            evidence=["evidence"],
        )

        result = update_knowledge_graph(state)
        assert "new_topic" in result["topics_evaluated"]
        assert "existing_topic" in result["topics_evaluated"]

    def test_does_not_mutate_original_state(self):
        original_kg = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="http_fundamentals", confidence=0.5, bloom_level=BloomLevel.understand
                )
            ],
            edges=[],
        )
        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["knowledge_graph"] = original_kg
        state["question_history"] = [
            Question(
                id="q-1",
                topic="http_fundamentals",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
        ]
        state["latest_evaluation"] = EvaluationResult(
            question_id="q-1",
            confidence=0.9,
            bloom_level=BloomLevel.apply,
            evidence=["new"],
        )

        result = update_knowledge_graph(state)
        # Original should be unchanged
        assert original_kg.get_node("http_fundamentals").confidence == 0.5
        # Result should be different
        assert result["knowledge_graph"].get_node("http_fundamentals").confidence != 0.5


class TestResponseEvaluator:
    @pytest.mark.asyncio
    async def test_evaluates_response(self):
        mock_output = EvaluationOutput(
            confidence=0.75,
            bloom_level="apply",
            evidence=["Good answer"],
            reasoning="Solid",
        )

        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["question_history"] = [
            Question(
                id="q-1",
                topic="http_fundamentals",
                bloom_level=BloomLevel.apply,
                text="Explain HTTP.",
                question_type="conceptual",
            )
        ]
        state["response_history"] = [
            Response(question_id="q-1", text="HTTP is a protocol for web communication.")
        ]

        with patch(
            "app.agents.response_evaluator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.return_value = mock_output
            result = await evaluate_response(state)

        ev = result["latest_evaluation"]
        assert ev.confidence == 0.75
        assert ev.bloom_level == BloomLevel.apply
        assert "Good answer" in ev.evidence

    @pytest.mark.asyncio
    async def test_clamps_confidence_to_valid_range(self):
        mock_output = EvaluationOutput(
            confidence=1.5,
            bloom_level="apply",
            evidence=["Over-confident"],
            reasoning="Test",
        )

        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["question_history"] = [
            Question(
                id="q-1",
                topic="http_fundamentals",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
        ]
        state["response_history"] = [Response(question_id="q-1", text="Answer")]

        with patch(
            "app.agents.response_evaluator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.return_value = mock_output
            result = await evaluate_response(state)

        assert result["latest_evaluation"].confidence == 1.0

    @pytest.mark.asyncio
    async def test_clamps_confidence_below_zero(self):
        mock_output = EvaluationOutput(
            confidence=-0.5,
            bloom_level="remember",
            evidence=["Negative confidence"],
            reasoning="Test",
        )

        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["question_history"] = [
            Question(
                id="q-1",
                topic="http_fundamentals",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
        ]
        state["response_history"] = [Response(question_id="q-1", text="Answer")]

        with patch(
            "app.agents.response_evaluator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.return_value = mock_output
            result = await evaluate_response(state)

        assert result["latest_evaluation"].confidence == 0.0

    @pytest.mark.asyncio
    async def test_llm_error_propagates(self):
        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["question_history"] = [
            Question(
                id="q-1",
                topic="http_fundamentals",
                bloom_level=BloomLevel.apply,
                text="Q?",
                question_type="conceptual",
            )
        ]
        state["response_history"] = [Response(question_id="q-1", text="Answer")]

        with patch(
            "app.agents.response_evaluator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.side_effect = RuntimeError("LLM error")
            with pytest.raises(RuntimeError, match="LLM error"):
                await evaluate_response(state)


class TestQuestionGenerator:
    @pytest.mark.asyncio
    async def test_generates_question(self):
        mock_output = QuestionOutput(
            topic="http_fundamentals",
            bloom_level="apply",
            text="Design a REST endpoint.",
            question_type="design",
        )

        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["current_topic"] = "http_fundamentals"
        state["current_bloom_level"] = BloomLevel.apply

        with patch(
            "app.agents.question_generator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.return_value = mock_output
            result = await generate_question(state)

        assert result["pending_question"] is not None
        assert result["pending_question"].text == "Design a REST endpoint."
        assert result["pending_question"].question_type == "design"
        assert len(result["question_history"]) == 1

    @pytest.mark.asyncio
    async def test_increments_question_counter(self):
        mock_output = QuestionOutput(
            topic="http_fundamentals",
            bloom_level="apply",
            text="Another question.",
            question_type="scenario",
        )

        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["current_topic"] = "http_fundamentals"
        state["current_bloom_level"] = BloomLevel.apply
        state["questions_on_current_topic"] = 2

        with patch(
            "app.agents.question_generator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.return_value = mock_output
            result = await generate_question(state)

        assert result["questions_on_current_topic"] == 3

    @pytest.mark.asyncio
    async def test_fallback_topic_when_empty(self):
        mock_output = QuestionOutput(
            topic="",
            bloom_level="apply",
            text="Fallback question.",
            question_type="conceptual",
        )

        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["current_topic"] = "http_fundamentals"
        state["current_bloom_level"] = BloomLevel.apply

        with patch(
            "app.agents.question_generator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.return_value = mock_output
            result = await generate_question(state)

        assert result["pending_question"].topic == "http_fundamentals"

    @pytest.mark.asyncio
    async def test_fallback_bloom_when_empty(self):
        mock_output = QuestionOutput(
            topic="http_fundamentals",
            bloom_level="",
            text="Fallback bloom.",
            question_type="conceptual",
        )

        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["current_topic"] = "http_fundamentals"
        state["current_bloom_level"] = BloomLevel.apply

        with patch(
            "app.agents.question_generator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.return_value = mock_output
            result = await generate_question(state)

        assert result["pending_question"].bloom_level == BloomLevel.apply

    @pytest.mark.asyncio
    async def test_fallback_question_type_when_empty(self):
        mock_output = QuestionOutput(
            topic="http_fundamentals",
            bloom_level="apply",
            text="Fallback type.",
            question_type="",
        )

        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["current_topic"] = "http_fundamentals"
        state["current_bloom_level"] = BloomLevel.apply

        with patch(
            "app.agents.question_generator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.return_value = mock_output
            result = await generate_question(state)

        assert result["pending_question"].question_type == "conceptual"

    @pytest.mark.asyncio
    async def test_llm_error_propagates(self):
        state = make_initial_state("test", ["nodejs"], "backend_engineering")
        state["current_topic"] = "http_fundamentals"
        state["current_bloom_level"] = BloomLevel.apply

        with patch(
            "app.agents.question_generator.ainvoke_structured", new_callable=AsyncMock
        ) as mock_invoke:
            mock_invoke.side_effect = RuntimeError("LLM error")
            with pytest.raises(RuntimeError, match="LLM error"):
                await generate_question(state)
