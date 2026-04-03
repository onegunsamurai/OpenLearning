"""Tests for the LangGraph pipeline structure and graph compilation."""

import pytest

from app.graph.pipeline import build_graph, compile_graph
from app.graph.state import LEVEL_BLOOM_MAP, BloomLevel, make_initial_state


class TestGraphStructure:
    def test_build_graph_has_expected_nodes(self):
        graph = build_graph()
        node_names = set(graph.nodes.keys())
        expected_nodes = {
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

    def test_no_calibration_nodes(self):
        graph = build_graph()
        node_names = set(graph.nodes.keys())
        calibration_nodes = {
            "calibrate_easy",
            "calibrate_medium",
            "calibrate_hard",
            "calibrate_evaluate",
        }
        assert not calibration_nodes & node_names, (
            f"Unexpected calibration nodes: {calibration_nodes & node_names}"
        )

    def test_compile_graph_returns_compiled(self):
        from langgraph.checkpoint.memory import MemorySaver

        compiled = compile_graph(checkpointer=MemorySaver())
        assert compiled is not None
        assert hasattr(compiled, "invoke")
        assert hasattr(compiled, "get_state")

    def test_graph_starts_with_build_agenda(self):
        graph = build_graph()
        edges = graph.edges
        start_edges = [e for e in edges if e[0] == "__start__"]
        assert len(start_edges) == 1
        assert start_edges[0][1] == "build_agenda"

    def test_agenda_to_assessment_edge(self):
        graph = build_graph()
        edges = set(graph.edges)
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

    def test_enrich_gaps_node_present(self):
        graph = build_graph()
        assert "enrich_gaps" in graph.nodes


class TestBuildAgendaBloomMapping:
    """Verify build_agenda_node maps target_level to correct starting Bloom level."""

    @pytest.mark.parametrize(
        "target_level,expected_bloom",
        [
            ("junior", BloomLevel.understand),
            ("mid", BloomLevel.apply),
            ("senior", BloomLevel.analyze),
            ("staff", BloomLevel.evaluate),
        ],
    )
    def test_target_level_maps_to_bloom(self, target_level, expected_bloom, monkeypatch):
        from app.graph import pipeline as pipeline_mod

        # Stub agenda builder to return a single item
        from app.graph.state import AgendaItem

        def fake_agenda(domain, level, skill_ids=None):
            return [AgendaItem(concept="test_topic", level=level)]

        monkeypatch.setattr(
            "app.knowledge_base.loader.build_topic_agenda_from_concepts",
            fake_agenda,
        )

        state = make_initial_state(
            candidate_id="test",
            skill_ids=["test_topic"],
            skill_domain="backend_engineering",
            target_level=target_level,
        )
        result = pipeline_mod.build_agenda_node(state)

        assert result["current_bloom_level"] == expected_bloom

    def test_unknown_level_defaults_to_apply(self, monkeypatch):
        from app.graph import pipeline as pipeline_mod
        from app.graph.state import AgendaItem

        def fake_agenda(domain, level, skill_ids=None):
            return [AgendaItem(concept="test_topic", level=level)]

        monkeypatch.setattr(
            "app.knowledge_base.loader.build_topic_agenda_from_concepts",
            fake_agenda,
        )

        state = make_initial_state(
            candidate_id="test",
            skill_ids=["test_topic"],
            skill_domain="backend_engineering",
            target_level="unknown_level",
        )
        result = pipeline_mod.build_agenda_node(state)

        assert result["current_bloom_level"] == BloomLevel.apply


class TestLevelBloomMap:
    """Verify the shared LEVEL_BLOOM_MAP constant."""

    def test_all_four_levels_present(self):
        assert set(LEVEL_BLOOM_MAP.keys()) == {"junior", "mid", "senior", "staff"}

    def test_values_are_bloom_levels(self):
        for value in LEVEL_BLOOM_MAP.values():
            assert isinstance(value, BloomLevel)
