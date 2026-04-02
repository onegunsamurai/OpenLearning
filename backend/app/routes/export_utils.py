from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse


def _safe_url(url: str) -> str | None:
    """Return the URL only if it uses http or https scheme."""
    try:
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https"):
            return url
    except Exception:
        pass
    return None


def build_assessment_markdown(
    session_id: str,
    target_level: str,
    completed_at: datetime | None,
    knowledge_graph: dict | None,
    gap_nodes: list[dict] | None,
    learning_plan: dict | None,
    proficiency_scores: list[dict] | None,
    materials: list[dict] | None = None,
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
                f"| {s.get('skill_name', s.get('skill_id', '—'))} "
                f"| {s.get('score', 0)}% "
                f"| {s.get('confidence', 0):.0%} "
                f"| {s.get('bloom_level', '—')} |"
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
            prereq_str = ", ".join(prereqs) if prereqs else "None"
            parts.append(f"### {node.get('concept', 'Unknown')}")
            parts.append(f"- **Confidence:** {confidence_pct}%")
            parts.append(f"- **Bloom Level:** {node.get('bloom_level', '—')}")
            parts.append(f"- **Prerequisites:** {prereq_str}")
            evidence = node.get("evidence", [])
            if evidence:
                parts.append(f"- **Evidence:** {'; '.join(evidence[:3])}")
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
            prereq_str = ", ".join(prereqs) if prereqs else "None"
            parts.append(f"### {i}. {gap.get('concept', 'Unknown')}")
            parts.append(f"- **Current Confidence:** {confidence_pct}%")
            parts.append(f"- **Target Bloom Level:** {gap.get('bloom_level', '—')}")
            parts.append(f"- **Prerequisites:** {prereq_str}")
            parts.append("")
    else:
        parts.append("*No gaps identified.*\n")

    # Learning Plan
    parts.append("---\n")
    parts.append("## Learning Plan\n")
    if learning_plan:
        parts.append(f"> {learning_plan.get('summary', '')}\n")
        total_hours = learning_plan.get("total_hours", 0)
        parts.append(f"**Total estimated time:** {total_hours} hours\n")
        for phase in learning_plan.get("phases", []):
            phase_num = phase.get("phase_number", "?")
            title = phase.get("title", "Untitled Phase")
            est_hours = phase.get("estimated_hours", 0)
            parts.append(f"### Phase {phase_num}: {title} ({est_hours}h)\n")
            parts.append(phase.get("rationale", ""))
            concepts = phase.get("concepts", [])
            if concepts:
                parts.append(f"\n**Concepts:** {', '.join(concepts)}\n")
            resources = phase.get("resources", [])
            if resources:
                parts.append("**Resources:**")
                for r in resources:
                    title_r = r.get("title", "Resource")
                    url = r.get("url")
                    rtype = r.get("type", "")
                    safe_url = _safe_url(url) if url else None
                    if safe_url:
                        parts.append(f"- [{title_r}]({safe_url}) — {rtype}")
                    else:
                        parts.append(f"- {title_r} — {rtype}")
            parts.append("")
    else:
        parts.append("*Learning plan not yet generated.*\n")

    # Generated Learning Materials
    if materials:
        parts.append("---\n")
        parts.append("## Generated Learning Materials\n")
        for mat in materials:
            mat_data = mat.get("material", {})
            concept_id = mat.get("concept_id", "Unknown")
            concept_title = concept_id.replace("_", " ").title()
            quality_score = mat.get("quality_score", 0)
            bloom_score = mat.get("bloom_score", 0)
            quality_flag = mat.get("quality_flag")

            parts.append(f"### {concept_title}\n")
            flag_str = f" | **Flag:** {quality_flag}" if quality_flag else ""
            parts.append(
                f"**Quality:** {quality_score:.0%} | **Bloom Score:** {bloom_score:.0%}{flag_str}\n"
            )

            sections = mat_data.get("sections", [])
            if not isinstance(sections, list):
                continue

            for section in sections:
                if not isinstance(section, dict):
                    continue
                sec_type = section.get("type", "")
                sec_title = section.get("title", "")
                sec_body = section.get("body", "")
                code_block = section.get("code_block")
                answer = section.get("answer")

                if not sec_title and not sec_body:
                    continue

                parts.append(f"#### {sec_title}\n")
                if sec_body:
                    parts.append(f"{sec_body}\n")
                if code_block:
                    parts.append(f"~~~~\n{code_block}\n~~~~\n")
                if sec_type == "quiz" and answer:
                    parts.append(f"> **Answer:** {answer}\n")
            parts.append("")

    parts.append("---")
    parts.append("\n*Generated by OpenLearning*")

    return "\n".join(parts)
