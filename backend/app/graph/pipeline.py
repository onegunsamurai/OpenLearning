from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.calibrator import (
    DIFFICULTY_LEVELS,
    evaluate_calibration,
    generate_calibration_question,
)
from app.agents.gap_analyzer import analyze_gaps
from app.agents.knowledge_mapper import update_knowledge_graph
from app.agents.plan_generator import generate_plan
from app.agents.question_generator import generate_question
from app.agents.response_evaluator import evaluate_response
from app.graph.router import MAX_TOTAL_QUESTIONS, decide_branch, get_deeper_bloom, get_next_topic
from app.graph.state import AssessmentState, Response

# --- Calibration nodes (one interrupt per node) ---


async def calibrate_easy(state: AssessmentState) -> dict:
    """Generate easy calibration question, interrupt for response, store result."""
    question = await generate_calibration_question(state, DIFFICULTY_LEVELS[0])
    user_answer = interrupt(
        {
            "type": "calibration",
            "question": question.model_dump(by_alias=True),
            "step": 1,
            "total_steps": len(DIFFICULTY_LEVELS),
        }
    )
    calibration_questions = list(state.get("calibration_questions", []))
    calibration_responses = list(state.get("calibration_responses", []))
    calibration_questions.append(question)
    calibration_responses.append(Response(question_id=question.id, text=user_answer))
    return {
        "calibration_questions": calibration_questions,
        "calibration_responses": calibration_responses,
    }


async def calibrate_medium(state: AssessmentState) -> dict:
    """Generate medium calibration question, interrupt for response, store result."""
    question = await generate_calibration_question(state, DIFFICULTY_LEVELS[1])
    user_answer = interrupt(
        {
            "type": "calibration",
            "question": question.model_dump(by_alias=True),
            "step": 2,
            "total_steps": len(DIFFICULTY_LEVELS),
        }
    )
    calibration_questions = list(state.get("calibration_questions", []))
    calibration_responses = list(state.get("calibration_responses", []))
    calibration_questions.append(question)
    calibration_responses.append(Response(question_id=question.id, text=user_answer))
    return {
        "calibration_questions": calibration_questions,
        "calibration_responses": calibration_responses,
    }


async def calibrate_hard(state: AssessmentState) -> dict:
    """Generate hard calibration question, interrupt for response, store result."""
    question = await generate_calibration_question(state, DIFFICULTY_LEVELS[2])
    user_answer = interrupt(
        {
            "type": "calibration",
            "question": question.model_dump(by_alias=True),
            "step": 3,
            "total_steps": len(DIFFICULTY_LEVELS),
        }
    )
    calibration_questions = list(state.get("calibration_questions", []))
    calibration_responses = list(state.get("calibration_responses", []))
    calibration_questions.append(question)
    calibration_responses.append(Response(question_id=question.id, text=user_answer))
    return {
        "calibration_questions": calibration_questions,
        "calibration_responses": calibration_responses,
    }


async def calibrate_evaluate(state: AssessmentState) -> dict:
    """Evaluate all 3 calibration Q&A pairs to determine starting level."""
    return await evaluate_calibration(state)


# --- Assessment question nodes (generate and await split) ---


async def generate_question_node(state: AssessmentState) -> dict:
    """Generate a question and store it in state. No interrupt here."""
    return await generate_question(state)


async def await_response_node(state: AssessmentState) -> dict:
    """Interrupt for user response to the pending question."""
    pending_q = state["pending_question"]
    user_answer = interrupt(
        {
            "type": "assessment",
            "question": pending_q.model_dump(by_alias=True),
            "topics_evaluated": len(state.get("topics_evaluated", [])),
            "total_questions": len(state.get("question_history", [])),
            "max_questions": MAX_TOTAL_QUESTIONS,
        }
    )
    response = Response(question_id=pending_q.id, text=user_answer)
    response_history = list(state.get("response_history", []))
    response_history.append(response)
    return {
        "response_history": response_history,
        "pending_question": None,
    }


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
    pending_q = state["pending_question"]
    user_answer = interrupt(
        {
            "type": "assessment",
            "question": pending_q.model_dump(by_alias=True),
            "topics_evaluated": len(state.get("topics_evaluated", [])),
            "total_questions": len(state.get("question_history", [])),
            "max_questions": MAX_TOTAL_QUESTIONS,
        }
    )
    response = Response(question_id=pending_q.id, text=user_answer)
    response_history = list(state.get("response_history", []))
    response_history.append(response)
    return {
        "response_history": response_history,
        "pending_question": None,
    }


def analyze_gaps_node(state: AssessmentState) -> dict:
    """Analyze gaps between current and target knowledge."""
    return analyze_gaps(state)


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

    # Calibration nodes
    graph.add_node("calibrate_easy", calibrate_easy)
    graph.add_node("calibrate_medium", calibrate_medium)
    graph.add_node("calibrate_hard", calibrate_hard)
    graph.add_node("calibrate_evaluate", calibrate_evaluate)

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
    graph.add_node("generate_plan", generate_plan_node)

    # Edges: calibration chain
    graph.add_edge(START, "calibrate_easy")
    graph.add_edge("calibrate_easy", "calibrate_medium")
    graph.add_edge("calibrate_medium", "calibrate_hard")
    graph.add_edge("calibrate_hard", "calibrate_evaluate")
    graph.add_edge("calibrate_evaluate", "generate_question")

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
    graph.add_edge("analyze_gaps", "generate_plan")
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
