from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.content_nodes import (
    gap_prioritizer,
    generate_all_content,
    input_reader,
    objective_generator,
    validate_all_content,
)
from app.graph.content_state import LearningMaterialState


def build_content_graph() -> StateGraph:
    """Build the learning content generation pipeline graph."""
    graph = StateGraph(LearningMaterialState)

    graph.add_node("input_reader", input_reader)
    graph.add_node("gap_prioritizer", gap_prioritizer)
    graph.add_node("objective_generator", objective_generator)
    graph.add_node("generate_all_content", generate_all_content)
    graph.add_node("validate_all_content", validate_all_content)

    graph.add_edge(START, "input_reader")
    graph.add_edge("input_reader", "gap_prioritizer")
    graph.add_edge("gap_prioritizer", "objective_generator")
    graph.add_edge("objective_generator", "generate_all_content")
    graph.add_edge("generate_all_content", "validate_all_content")
    graph.add_edge("validate_all_content", END)

    return graph


def compile_content_graph(checkpointer):
    """Compile the content pipeline graph with a checkpointer.

    Args:
        checkpointer: A LangGraph checkpointer instance (e.g.
            ``AsyncPostgresSaver`` or ``MemorySaver``).
    """
    graph = build_content_graph()
    return graph.compile(checkpointer=checkpointer)
