"""Tests for the LangGraph pipeline structure and graph compilation."""

from app.graph.pipeline import build_graph, compile_graph


class TestGraphStructure:
    def test_build_graph_has_expected_nodes(self):
        graph = build_graph()
        node_names = set(graph.nodes.keys())
        expected_nodes = {
            "calibrate_easy",
            "calibrate_medium",
            "calibrate_hard",
            "calibrate_evaluate",
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
        assert ("calibrate_evaluate", "generate_question") in edges

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
