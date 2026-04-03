from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.gap_analyzer import analyze_gaps
from app.agents.gap_enricher import enrich_gaps
from app.agents.knowledge_mapper import update_knowledge_graph
from app.agents.plan_generator import generate_plan
from app.agents.question_generator import generate_question
from app.agents.response_evaluator import evaluate_response
from app.graph.router import MAX_TOPICS, decide_branch, get_deeper_bloom, get_next_topic
from app.graph.state import (
    LEVEL_BLOOM_MAP,
    AssessmentState,
    BloomLevel,
    Question,
    Response,
    TopicStatus,
)

# --- Agenda node ---


def build_agenda_node(state: AssessmentState) -> dict:
    """Build the topic agenda and select the first topic.

    When skill_ids contain concept IDs (role-based selection), only those
    concepts are included in the agenda. Otherwise, all concepts up to the
    target level are used.
    """
    from app.knowledge_base.loader import build_topic_agenda, build_topic_agenda_from_concepts

    domain = state.get("skill_domain", "backend_engineering")
    target_level = state.get("target_level", "mid")
    skill_ids = state.get("skill_ids", [])

    # Build agenda: filtered to selected concepts when skill_ids are provided,
    # otherwise all concepts up to the target level.
    if skill_ids:
        agenda = build_topic_agenda_from_concepts(domain, target_level, skill_ids)
    else:
        agenda = build_topic_agenda(domain, target_level)

    # Mark the first topic as active
    if agenda:
        agenda[0].status = TopicStatus.active
        first_topic = agenda[0].concept
    else:
        first_topic = ""

    per_topic = state.get("max_questions_per_topic", 4)

    return {
        "topic_agenda": agenda,
        "current_topic": first_topic,
        "current_bloom_level": LEVEL_BLOOM_MAP.get(target_level, BloomLevel.apply),
        "questions_on_current_topic": 0,
        "max_questions_per_topic": per_topic,
    }


# --- Shared helpers ---


def _build_interrupt_payload(state: AssessmentState, pending_q: Question) -> dict:
    """Build the interrupt metadata dict shared by all response-await nodes."""
    agenda = state.get("topic_agenda", [])
    per_topic = state.get("max_questions_per_topic", 4)
    return {
        "type": "assessment",
        "question": pending_q.model_dump(by_alias=True),
        "topics_evaluated": len(state.get("topics_evaluated", [])),
        "total_questions": len(state.get("question_history", [])),
        "max_questions": min(len(agenda), MAX_TOPICS) * per_topic,
        "current_topic_name": state.get("current_topic", ""),
        "topics_remaining": sum(1 for item in agenda if item.status == TopicStatus.pending),
    }


def _await_and_record(state: AssessmentState) -> dict:
    """Interrupt for a user response and append it to response history."""
    pending_q = state["pending_question"]
    user_answer = interrupt(_build_interrupt_payload(state, pending_q))
    response = Response(question_id=pending_q.id, text=user_answer)
    response_history = list(state.get("response_history", []))
    response_history.append(response)
    return {
        "response_history": response_history,
        "pending_question": None,
    }


# --- Assessment question nodes (generate and await split) ---


async def generate_question_node(state: AssessmentState) -> dict:
    """Generate a question and store it in state. No interrupt here."""
    return await generate_question(state)


async def await_response_node(state: AssessmentState) -> dict:
    """Interrupt for user response to the pending question."""
    return _await_and_record(state)


async def evaluate_response_node(state: AssessmentState) -> dict:
    """Evaluate the candidate's latest response."""
    return await evaluate_response(state)


def update_graph_node(state: AssessmentState) -> dict:
    """Update knowledge graph with evaluation results."""
    return update_knowledge_graph(state)


# --- Probe nodes (generate and await split) ---


async def probe_question_node(state: AssessmentState) -> dict:
    """Generate a probing follow-up question on the same topic."""
    return await generate_question(state)


async def await_probe_response_node(state: AssessmentState) -> dict:
    """Interrupt for user response to the probe question."""
    return _await_and_record(state)


def analyze_gaps_node(state: AssessmentState) -> dict:
    """Analyze gaps between current and target knowledge."""
    return analyze_gaps(state)


async def enrich_gaps_node(state: AssessmentState) -> dict:
    """Enrich gap analysis with readiness, priority, and recommendations."""
    return await enrich_gaps(state)


async def generate_plan_node(state: AssessmentState) -> dict:
    """Generate learning plan from gaps."""
    return await generate_plan(state)


def handle_deeper(state: AssessmentState) -> dict:
    """Advance Bloom level before generating next question."""
    return get_deeper_bloom(state)


def handle_pivot(state: AssessmentState) -> dict:
    """Switch to next topic."""
    return get_next_topic(state)


# --- Graph wiring ---


def route_after_update(state: AssessmentState) -> str:
    return decide_branch(state)


def build_graph() -> StateGraph:
    graph = StateGraph(AssessmentState)

    # Agenda node
    graph.add_node("build_agenda", build_agenda_node)

    # Assessment nodes
    graph.add_node("generate_question", generate_question_node)
    graph.add_node("await_response", await_response_node)
    graph.add_node("evaluate_response", evaluate_response_node)
    graph.add_node("update_graph", update_graph_node)

    # Routing nodes
    graph.add_node("handle_deeper", handle_deeper)
    graph.add_node("handle_pivot", handle_pivot)

    # Probe nodes
    graph.add_node("probe_question", probe_question_node)
    graph.add_node("await_probe_response", await_probe_response_node)

    # Conclusion nodes
    graph.add_node("analyze_gaps", analyze_gaps_node)
    graph.add_node("enrich_gaps", enrich_gaps_node)
    graph.add_node("generate_plan", generate_plan_node)

    # Edges: start → agenda → assessment
    graph.add_edge(START, "build_agenda")
    graph.add_edge("build_agenda", "generate_question")

    # Edges: assessment loop
    graph.add_edge("generate_question", "await_response")
    graph.add_edge("await_response", "evaluate_response")
    graph.add_edge("evaluate_response", "update_graph")

    graph.add_conditional_edges(
        "update_graph",
        route_after_update,
        {
            "deeper": "handle_deeper",
            "pivot": "handle_pivot",
            "probe": "probe_question",
            "conclude": "analyze_gaps",
        },
    )

    graph.add_edge("handle_deeper", "generate_question")
    graph.add_edge("handle_pivot", "generate_question")

    # Probe loop
    graph.add_edge("probe_question", "await_probe_response")
    graph.add_edge("await_probe_response", "evaluate_response")

    # Conclusion
    graph.add_edge("analyze_gaps", "enrich_gaps")
    graph.add_edge("enrich_gaps", "generate_plan")
    graph.add_edge("generate_plan", END)

    return graph


def compile_graph(checkpointer):
    """Compile the assessment pipeline graph.

    Args:
        checkpointer: A LangGraph checkpointer instance (e.g.
            ``AsyncPostgresSaver`` or ``MemorySaver``).
    """
    graph = build_graph()
    return graph.compile(checkpointer=checkpointer)
