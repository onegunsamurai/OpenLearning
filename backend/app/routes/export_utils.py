from __future__ import annotations

from datetime import datetime

from app.services.assessment_mappers import normalize_phase_concepts

# Characters that enable markdown injection when unescaped in free text.
# Intentionally excludes `.+-{}!` — those require specific line-start
# positions to be interpreted as syntax and have low injection risk.
_MD_ESCAPE_CHARS = tuple("\\`*_[]()#|<>")


def _escape_md(text: str | None) -> str:
    """Escape markdown metacharacters in LLM-generated free text.

    Protects against markdown injection (``[evil](javascript:...)``), tables
    broken by embedded ``|``, headings injected via leading ``#``, raw HTML
    via ``<script>``). Applied at every insertion point where LLM output or
    user-provided strings enter the rendered markdown.

    Also collapses embedded newlines to spaces to prevent line-break-based
    injection (breaking out of list items, block quotes, or table rows).
    """
    if not text:
        return ""
    # Collapse newlines first — they break any markdown construct.
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    # Backslash must be handled first to avoid double-escaping.
    for ch in _MD_ESCAPE_CHARS:
        text = text.replace(ch, f"\\{ch}")
    return text


def _safe_url(url: str | None) -> str | None:
    """Return ``url`` only if it uses a safe HTTP(S) scheme, else ``None``.

    Prevents ``javascript:``, ``data:``, ``file:``, and other schemes from
    being embedded in ``[text](url)`` link syntax. Unsafe URLs are dropped
    and the caller should render the resource as plain text instead.
    Parentheses inside the URL are URL-encoded so they cannot terminate the
    markdown link early.  Whitespace and control characters are rejected
    because they can break out of the URL destination in markdown link
    syntax and reintroduce injection vectors.
    """
    if not url:
        return None
    url = url.strip()
    lowered = url.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        return None
    # Reject URLs containing whitespace or control characters — they can
    # break the markdown link destination and allow injection.
    if any(ch.isspace() or ord(ch) < 0x20 for ch in url):
        return None
    # Escape characters that break markdown link syntax.
    return url.replace("(", "%28").replace(")", "%29")


def _safe_cell(text: str | None) -> str:
    """Escape markdown metacharacters for table cell content.

    Delegates to ``_escape_md`` which already escapes pipes and collapses
    newlines — both of which break table row syntax.
    """
    return _escape_md(text)


def build_assessment_markdown(
    session_id: str,
    target_level: str,
    completed_at: datetime | None,
    knowledge_graph: dict | None,
    gap_nodes: list[dict] | None,
    learning_plan: dict | None,
    proficiency_scores: list[dict] | None,
) -> str:
    """
    Render an assessment result as formatted markdown.

    All dict arguments use snake_case keys, matching AssessmentResult DB storage
    (proficiency_scores stored via model_dump() without by_alias).
    """
    parts: list[str] = []

    # Header
    date_str = completed_at.strftime("%Y-%m-%d") if completed_at else "N/A"
    parts.append("# Assessment Report\n")
    parts.append(f"**Session:** `{session_id}`  ")
    parts.append(f"**Date:** {date_str}  ")
    parts.append(f"**Target Level:** {target_level}\n")
    parts.append("---\n")

    # Proficiency Scores table
    parts.append("## Proficiency Scores\n")
    if proficiency_scores:
        parts.append("| Skill | Score | Confidence | Bloom Level |")
        parts.append("|-------|-------|------------|-------------|")
        for s in proficiency_scores:
            parts.append(
                f"| {_safe_cell(s.get('skill_name', s.get('skill_id', '—')))} "
                f"| {s.get('score', 0)}% "
                f"| {s.get('confidence', 0):.0%} "
                f"| {_safe_cell(s.get('bloom_level', '—'))} |"
            )
    else:
        parts.append("*No proficiency scores available.*")
    parts.append("")

    # Knowledge Graph
    parts.append("---\n")
    parts.append("## Knowledge Map\n")
    nodes = (knowledge_graph or {}).get("nodes", [])
    if nodes:
        for node in nodes:
            confidence_pct = int(node.get("confidence", 0) * 100)
            prereqs = node.get("prerequisites", [])
            prereq_str = ", ".join(_escape_md(p) for p in prereqs) if prereqs else "None"
            parts.append(f"### {_escape_md(node.get('concept', 'Unknown'))}")
            parts.append(f"- **Confidence:** {confidence_pct}%")
            parts.append(f"- **Bloom Level:** {_escape_md(node.get('bloom_level', '—'))}")
            parts.append(f"- **Prerequisites:** {prereq_str}")
            evidence = node.get("evidence", [])
            if evidence:
                parts.append(f"- **Evidence:** {'; '.join(_escape_md(e) for e in evidence[:3])}")
            parts.append("")
    else:
        parts.append("*Assessment not yet complete — knowledge map unavailable.*\n")

    # Gap Nodes
    parts.append("---\n")
    parts.append("## Knowledge Gaps\n")
    if gap_nodes:
        parts.append(
            f"The following {len(gap_nodes)} area(s) were identified as requiring attention:\n"
        )
        for i, gap in enumerate(gap_nodes, 1):
            confidence_pct = int(gap.get("confidence", 0) * 100)
            prereqs = gap.get("prerequisites", [])
            prereq_str = ", ".join(_escape_md(p) for p in prereqs) if prereqs else "None"
            parts.append(f"### {i}\\. {_escape_md(gap.get('concept', 'Unknown'))}")
            parts.append(f"- **Current Confidence:** {confidence_pct}%")
            parts.append(f"- **Target Bloom Level:** {_escape_md(gap.get('bloom_level', '—'))}")
            parts.append(f"- **Prerequisites:** {prereq_str}")
            parts.append("")
    else:
        parts.append("*No gaps identified.*\n")

    # Learning Plan
    parts.append("---\n")
    parts.append("## Learning Plan\n")
    if learning_plan:
        parts.append(f"> {_escape_md(learning_plan.get('summary', ''))}\n")
        total_hours = learning_plan.get("total_hours", 0)
        parts.append(f"**Total estimated time:** {total_hours} hours\n")
        for phase in learning_plan.get("phases", []):
            phase_num = phase.get("phase_number", "?")
            title = _escape_md(phase.get("title", "Untitled Phase"))
            est_hours = phase.get("estimated_hours", 0)
            parts.append(f"### Phase {phase_num}: {title} ({est_hours}h)\n")
            parts.append(_escape_md(phase.get("rationale", "")))
            # normalize_phase_concepts handles both the new nested shape and
            # legacy list[str] rows stored before issue #168.
            for concept in normalize_phase_concepts(phase):
                parts.append(f"\n#### {_escape_md(concept.get('name', ''))}")
                description = concept.get("description", "")
                if description:
                    parts.append(_escape_md(description))
                resources = concept.get("resources", [])
                if resources:
                    parts.append("**Resources:**")
                    for r in resources:
                        title_r = _escape_md(r.get("title", "Resource"))
                        url = _safe_url(r.get("url"))
                        rtype = _escape_md(r.get("type", ""))
                        if url:
                            parts.append(f"- [{title_r}]({url}) — {rtype}")
                        else:
                            parts.append(f"- {title_r} — {rtype}")
            parts.append("")
    else:
        parts.append("*Learning plan not yet generated.*\n")

    parts.append("---")
    parts.append("\n*Generated by OpenLearning*")

    return "\n".join(parts)
