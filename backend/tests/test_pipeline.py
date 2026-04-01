"""Tests for the LangGraph pipeline structure and graph compilation."""

import pytest

from app.graph.pipeline import (
    _make_calibration_node,
    build_graph,
    calibrate_easy,
    calibrate_hard,
    calibrate_medium,
    compile_graph,
)


class TestGraphStructure:
    def test_build_graph_has_expected_nodes(self):
        graph = build_graph()
        node_names = set(graph.nodes.keys())
        expected_nodes = {
            "calibrate_easy",
            "calibrate_medium",
            "calibrate_hard",
            "calibrate_evaluate",
            "build_agenda",
            "handle_deeper",
            "handle_pivot",
            "generate_question",
            "await_response",
            "evaluate_response",
            "update_graph",
            "probe_question",
            "await_probe_response",
            "analyze_gaps",
            "generate_plan",
        }
        assert expected_nodes.issubset(node_names), f"Missing nodes: {expected_nodes - node_names}"

    def test_compile_graph_returns_compiled(self):
        from langgraph.checkpoint.memory import MemorySaver

        compiled = compile_graph(checkpointer=MemorySaver())
        assert compiled is not None
        assert hasattr(compiled, "invoke")
        assert hasattr(compiled, "get_state")

    def test_graph_starts_with_calibrate_easy(self):
        graph = build_graph()
        edges = graph.edges
        start_edges = [e for e in edges if e[0] == "__start__"]
        assert len(start_edges) == 1
        assert start_edges[0][1] == "calibrate_easy"

    def test_calibration_chain(self):
        graph = build_graph()
        edges = set(graph.edges)
        assert ("calibrate_easy", "calibrate_medium") in edges
        assert ("calibrate_medium", "calibrate_hard") in edges
        assert ("calibrate_hard", "calibrate_evaluate") in edges
        assert ("calibrate_evaluate", "build_agenda") in edges
        assert ("build_agenda", "generate_question") in edges

    def test_assessment_loop_edges(self):
        graph = build_graph()
        edges = set(graph.edges)
        assert ("generate_question", "await_response") in edges
        assert ("await_response", "evaluate_response") in edges
        assert ("evaluate_response", "update_graph") in edges

    def test_probe_edges(self):
        graph = build_graph()
        edges = set(graph.edges)
        assert ("probe_question", "await_probe_response") in edges
        assert ("await_probe_response", "evaluate_response") in edges

    def test_conclusion_edges(self):
        graph = build_graph()
        edges = set(graph.edges)
        assert ("analyze_gaps", "enrich_gaps") in edges
        assert ("enrich_gaps", "generate_plan") in edges


class TestCalibrationNodeFactory:
    """Verify the _make_calibration_node factory produces correct callables."""

    def test_factory_returns_async_callable(self):
        import asyncio

        node = _make_calibration_node(0)
        assert asyncio.iscoroutinefunction(node)

    def test_module_level_nodes_are_callables(self):
        import asyncio

        assert asyncio.iscoroutinefunction(calibrate_easy)
        assert asyncio.iscoroutinefunction(calibrate_medium)
        assert asyncio.iscoroutinefunction(calibrate_hard)

    def test_factory_creates_distinct_functions(self):
        assert calibrate_easy is not calibrate_medium
        assert calibrate_medium is not calibrate_hard
        assert calibrate_easy is not calibrate_hard

    def test_enrich_gaps_node_present(self):
        graph = build_graph()
        assert "enrich_gaps" in graph.nodes

    @pytest.mark.asyncio
    async def test_calibration_node_behavioral_contract(self, monkeypatch):
        """Verify the factory-produced node builds correct interrupt payload and state."""
        from unittest.mock import AsyncMock

        from app.graph import pipeline as pipeline_mod
        from app.graph.state import Question, Response

        fake_question = Question(
            id="q-test-123",
            text="What is a hash table?",
            topic="data_structures",
            bloom_level="remember",
            question_type="open",
        )
        monkeypatch.setattr(
            pipeline_mod,
            "generate_calibration_question",
            AsyncMock(return_value=fake_question),
        )

        captured_payload = {}

        def fake_interrupt(payload):
            captured_payload.update(payload)
            return "user answer text"

        monkeypatch.setattr(pipeline_mod, "interrupt", fake_interrupt)

        node = _make_calibration_node(1)  # difficulty_index=1 → step=2
        state = {"calibration_questions": [], "calibration_responses": []}
        result = await node(state)

        # Verify interrupt payload
        assert captured_payload["type"] == "calibration"
        assert captured_payload["step"] == 2
        assert captured_payload["total_steps"] == 3
        assert captured_payload["question"]["id"] == "q-test-123"

        # Verify returned state
        assert len(result["calibration_questions"]) == 1
        assert result["calibration_questions"][0] is fake_question
        assert len(result["calibration_responses"]) == 1
        assert isinstance(result["calibration_responses"][0], Response)
        assert result["calibration_responses"][0].text == "user answer text"
        assert result["calibration_responses"][0].question_id == "q-test-123"
