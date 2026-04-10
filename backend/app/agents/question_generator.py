from __future__ import annotations

import logging
import re
import uuid

from app.agents.schemas import QuestionOutput
from app.graph.state import (
    AssessmentState,
    BloomLevel,
    EvaluationResult,
    KnowledgeGraph,
    Question,
    bloom_index,
)
from app.prompts.question_gen import QUESTION_GEN_PROMPT
from app.services.ai import ainvoke_structured

logger = logging.getLogger("openlearning.assessment")

# ── Constants ───────────────────────────────────────────────────────────────

_SIGNAL_MAX_CHARS = 400  # SR-04 belt-and-braces cap
# 80 chars: tightened from the issue's 120-char default per threat-model SR-04
# to reduce attacker-controlled prompt surface.
_EVIDENCE_ITEM_CAP = 80
_EVIDENCE_COUNT_CAP = 2  # SR-01 / SR-04 count cap
_SIGNAL_WORD_CAP = 60  # ADR §(d) 60-word cap

# Strip all ASCII control chars (0x00-0x1f, including \t \n \r) plus DEL
# (0x7f). We then collapse any remaining whitespace runs.
_CONTROL_CHAR_TABLE = {c: None for c in range(0x00, 0x20)}
_CONTROL_CHAR_TABLE[0x7F] = None
_WHITESPACE_RE = re.compile(r"\s+")


# ── Helpers ─────────────────────────────────────────────────────────────────


def _sanitize_evidence(items: list[str]) -> list[str]:
    """Sanitize candidate-derived evidence strings before injection into a prompt.

    Defense-in-depth for SR-01 (prompt injection via evidence). Steps:
      1. Strip ASCII control chars and collapse whitespace runs to single spaces.
      2. Escape embedded double quotes and wrap each item in double quotes.
      3. Truncate each cleaned item to 80 chars with an ellipsis suffix.
      4. Return at most the first 2 items.
    """
    cleaned: list[str] = []
    for raw in items[:_EVIDENCE_COUNT_CAP]:
        if not isinstance(raw, str):
            try:
                raw = str(raw)
            except Exception:
                continue
        stripped = raw.translate(_CONTROL_CHAR_TABLE)
        collapsed = _WHITESPACE_RE.sub(" ", stripped).strip()
        if not collapsed:
            continue
        if len(collapsed) > _EVIDENCE_ITEM_CAP:
            # Reserve 1 char for the ellipsis so the final cleaned item
            # length (including "…") is exactly _EVIDENCE_ITEM_CAP.
            collapsed = collapsed[: _EVIDENCE_ITEM_CAP - 1] + "…"
        escaped = collapsed.replace('"', '\\"')
        cleaned.append(f'"{escaped}"')
    return cleaned


def _confidence_band(confidence: float) -> str:
    """Map a 0..1 confidence score to a qualitative band."""
    if confidence > 0.7:
        return "strong"
    if confidence >= 0.4:
        return "partial"
    return "weak"


def _bloom_delta_phrase(demonstrated: BloomLevel, target: BloomLevel) -> str:
    """Return a short phrase describing demonstrated vs. target Bloom gap."""
    try:
        demo_idx = bloom_index(demonstrated)
        target_idx = bloom_index(target)
    except ValueError:
        return ""
    delta = demo_idx - target_idx
    if delta == 0:
        return "matched target"
    if delta > 0:
        return f"overshoot by {delta} (above target)"
    return f"undershoot by {abs(delta)} (below target)"


def _coerce_bloom(value: object) -> BloomLevel | None:
    """Best-effort coercion of a checkpoint-deserialized bloom value."""
    if isinstance(value, BloomLevel):
        return value
    if isinstance(value, str):
        try:
            return BloomLevel(value)
        except ValueError:
            return None
    return None


def _cap_signal(signal: str) -> str:
    """Apply word cap then hard char cap with ellipsis (SR-04)."""
    words = signal.split()
    if len(words) > _SIGNAL_WORD_CAP:
        signal = " ".join(words[:_SIGNAL_WORD_CAP]) + "…"
    if len(signal) > _SIGNAL_MAX_CHARS:
        signal = signal[: _SIGNAL_MAX_CHARS - 1] + "…"
    return signal


def _has_meaningful_evaluation(ev: EvaluationResult | None) -> bool:
    """True iff latest_evaluation carries real data (not the init stub)."""
    if ev is None:
        return False
    return bool(getattr(ev, "question_id", ""))


def _signal_from_evaluation(ev: EvaluationResult, target_bloom: BloomLevel) -> str:
    """Compose the performance signal from a real latest_evaluation."""
    try:
        confidence = max(0.0, min(1.0, float(ev.confidence)))
    except (TypeError, ValueError):
        confidence = 0.0
    band = _confidence_band(confidence)
    demo_bloom = _coerce_bloom(ev.bloom_level)
    delta_phrase = _bloom_delta_phrase(demo_bloom, target_bloom) if demo_bloom else ""
    demo_name = demo_bloom.value if demo_bloom else "unknown"

    parts = [
        f"{band} grasp (confidence={confidence:.2f}); "
        f"demonstrated Bloom={demo_name} vs target={target_bloom.value}"
    ]
    if delta_phrase:
        parts.append(f" [{delta_phrase}]")
    parts.append(".")

    raw_evidence = ev.evidence if isinstance(ev.evidence, list) else []
    sanitized = _sanitize_evidence(raw_evidence)
    if sanitized:
        parts.append(" Evidence: " + "; ".join(sanitized) + ".")
    return "".join(parts)


def _signal_from_knowledge_graph(kg: KnowledgeGraph, topic: str) -> str | None:
    """Fallback signal derived from a knowledge-graph node, if any."""
    if not isinstance(kg, KnowledgeGraph):
        return None
    node = kg.get_node(topic)
    if node is None:
        return None
    try:
        confidence = max(0.0, min(1.0, float(node.confidence)))
    except (TypeError, ValueError):
        confidence = 0.0
    band = _confidence_band(confidence)
    node_bloom = _coerce_bloom(node.bloom_level)
    bloom_name = node_bloom.value if node_bloom else "unknown"
    parts = [f"prior {band} grasp on {topic} (confidence={confidence:.2f}, Bloom={bloom_name})."]
    sanitized = _sanitize_evidence(list(node.evidence) if isinstance(node.evidence, list) else [])
    if sanitized:
        parts.append(" Evidence: " + "; ".join(sanitized) + ".")
    return "".join(parts)


def build_performance_signal(state: AssessmentState) -> str:
    """Derive a bounded adaptive signal for the next question generation.

    Returns a short human-readable summary of the candidate's most recent
    evaluation (or knowledge-graph fallback) so the question generator can
    escalate / probe / pivot. Pure function; tolerant of malformed state.
    Never raises. Output is capped at ~60 words and 400 chars.
    """
    try:
        topic = str(state.get("current_topic") or "").strip()
        target_bloom = _coerce_bloom(state.get("current_bloom_level")) or BloomLevel.understand
        questions_on_topic = int(state.get("questions_on_current_topic") or 0)
        latest: EvaluationResult | None = state.get("latest_evaluation")

        # R4: distinguish the true first-question case from the
        # later-question / no-evaluation case so the LLM isn't misled into
        # treating a mid-topic question like an opener.
        if questions_on_topic == 0:
            return "none (first question in assessment)"

        if not _has_meaningful_evaluation(latest):
            # Try KG fallback before giving up — we already asked questions
            # on this topic, so prior knowledge may exist.
            if topic:
                kg_signal = _signal_from_knowledge_graph(
                    state.get("knowledge_graph") or KnowledgeGraph(), topic
                )
                if kg_signal:
                    return _cap_signal(kg_signal)
            return "none (no evaluation yet)"

        return _cap_signal(_signal_from_evaluation(latest, target_bloom))
    except Exception:
        # SR-02: never raise. Fall back to a safe sentinel, but log so operators
        # can see silent degradation rather than debugging blind.
        logger.warning(
            "build_performance_signal failed; returning sentinel",
            exc_info=True,
        )
        return "none (signal unavailable)"


# ── Main entry point ────────────────────────────────────────────────────────


async def generate_question(state: AssessmentState) -> dict:
    """Generate the next assessment question based on current state."""
    topic = state["current_topic"]
    bloom_level = state["current_bloom_level"]
    questions_on_topic = state.get("questions_on_current_topic", 0)

    # Collect previously used question types for this topic
    used_types = [q.question_type for q in state.get("question_history", []) if q.topic == topic]

    # Format previous questions for context
    prev_questions = (
        "\n".join(f"- [{q.topic}] {q.text}" for q in state.get("question_history", [])[-5:])
        or "None yet."
    )

    # bloom_level may be a string after checkpoint deserialization
    bloom_str = bloom_level.value if isinstance(bloom_level, BloomLevel) else str(bloom_level)

    performance_signal = build_performance_signal(state)

    prompt = QUESTION_GEN_PROMPT.format(
        topic=topic,
        bloom_level=bloom_str,
        used_types=", ".join(used_types) if used_types else "none",
        previous_questions=prev_questions,
        performance_signal=performance_signal,
    )

    result = await ainvoke_structured(
        QuestionOutput,
        prompt,
        agent_name="question_generator.generate",
    )

    question = Question(
        id=str(uuid.uuid4()),
        topic=result.topic or topic,
        bloom_level=BloomLevel(result.bloom_level or bloom_str),
        text=result.text,
        question_type=result.question_type or "conceptual",
    )

    question_history = list(state.get("question_history", []))
    question_history.append(question)

    return {
        "question_history": question_history,
        "pending_question": question,
        "questions_on_current_topic": questions_on_topic + 1,
    }
