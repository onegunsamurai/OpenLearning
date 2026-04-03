from __future__ import annotations

from collections import deque
from pathlib import Path

import yaml

from app.knowledge_base.schema import LEVEL_ORDER, KnowledgeBaseSchema
from app.models.assessment_pipeline import AgendaItem, TopicStatus
from app.models.bloom import BloomLevel
from app.models.knowledge import KnowledgeGraph, KnowledgeNode

_KB_DIR = Path(__file__).parent
_cache: dict[str, KnowledgeBaseSchema] = {}
_domain_path_cache: dict[str, Path] | None = None


def _get_domain_paths() -> dict[str, Path]:
    """Return a cached mapping of domain name → resolved Path from filesystem enumeration."""
    global _domain_path_cache
    if _domain_path_cache is not None:
        return _domain_path_cache
    _domain_path_cache = {p.stem: p for p in _KB_DIR.glob("*.yaml")}
    return _domain_path_cache


def load_knowledge_base(domain: str) -> KnowledgeBaseSchema:
    if domain in _cache:
        return _cache[domain]
    domain_paths = _get_domain_paths()
    if domain not in domain_paths:
        raise FileNotFoundError(f"Knowledge base not found: {domain}")
    with open(domain_paths[domain]) as f:
        data = yaml.safe_load(f)
    kb = KnowledgeBaseSchema(**data)
    _cache[domain] = kb
    return kb


def list_domains() -> list[str]:
    """Return sorted list of all available knowledge base domain names."""
    return sorted(_get_domain_paths().keys())


def clear_cache() -> None:
    """Clear all caches. Useful for tests."""
    global _domain_path_cache
    _cache.clear()
    _domain_path_cache = None


def get_target_graph(domain: str, level: str) -> KnowledgeGraph:
    """Build a KnowledgeGraph containing all concepts up to and including the target level."""
    kb = load_knowledge_base(domain)
    if level not in LEVEL_ORDER:
        raise ValueError(f"Unknown level: {level}. Must be one of {LEVEL_ORDER}")

    target_idx = LEVEL_ORDER.index(level)
    nodes: list[KnowledgeNode] = []
    edges: list[tuple[str, str]] = []
    seen_concepts: set[str] = set()

    for lvl in LEVEL_ORDER[: target_idx + 1]:
        level_data = kb.levels.get(lvl)
        if not level_data:
            continue
        for concept_data in level_data.concepts:
            if concept_data.concept in seen_concepts:
                continue
            seen_concepts.add(concept_data.concept)
            nodes.append(
                KnowledgeNode(
                    concept=concept_data.concept,
                    confidence=concept_data.target_confidence,
                    bloom_level=BloomLevel(concept_data.bloom_target),
                    prerequisites=concept_data.prerequisites,
                    evidence=[],
                )
            )
            for prereq in concept_data.prerequisites:
                edges.append((prereq, concept_data.concept))

    return KnowledgeGraph(nodes=nodes, edges=edges)


def get_topics_for_level(domain: str, level: str) -> list[str]:
    """Get the topic names for a specific level."""
    kb = load_knowledge_base(domain)
    level_data = kb.levels.get(level)
    if not level_data:
        return []
    return [c.concept for c in level_data.concepts]


def get_all_topics(domain: str, up_to_level: str) -> list[str]:
    """Get all topic names up to and including the given level."""
    graph = get_target_graph(domain, up_to_level)
    return [node.concept for node in graph.nodes]


def build_topic_agenda(domain: str, target_level: str) -> list[AgendaItem]:
    """Build a topic agenda sorted by prerequisite order (fundamentals first).

    Uses Kahn's algorithm for topological sort. Topics with no prerequisites
    come first, then their dependents, ensuring the interviewer starts with
    fundamentals and works up.
    """
    kb = load_knowledge_base(domain)
    if target_level not in LEVEL_ORDER:
        raise ValueError(f"Unknown level: {target_level}. Must be one of {LEVEL_ORDER}")

    target_idx = LEVEL_ORDER.index(target_level)

    # Collect all concepts up to target level with their metadata
    concept_level: dict[str, str] = {}
    concept_prereqs: dict[str, list[str]] = {}

    for lvl in LEVEL_ORDER[: target_idx + 1]:
        level_data = kb.levels.get(lvl)
        if not level_data:
            continue
        for c in level_data.concepts:
            if c.concept not in concept_level:
                concept_level[c.concept] = lvl
                concept_prereqs[c.concept] = c.prerequisites

    # Kahn's topological sort
    in_degree: dict[str, int] = {c: 0 for c in concept_level}
    for concept, prereqs in concept_prereqs.items():
        for prereq in prereqs:
            if prereq in in_degree:
                in_degree[concept] += 1

    queue: deque[str] = deque(c for c, d in in_degree.items() if d == 0)
    sorted_concepts: list[str] = []

    while queue:
        current = queue.popleft()
        sorted_concepts.append(current)
        # Find dependents (concepts that list current as a prerequisite)
        for concept, prereqs in concept_prereqs.items():
            if current in prereqs:
                in_degree[concept] -= 1
                if in_degree[concept] == 0:
                    queue.append(concept)

    # Any remaining concepts (cycles or missing prereqs) go at the end
    for concept in concept_level:
        if concept not in sorted_concepts:
            sorted_concepts.append(concept)

    return [
        AgendaItem(
            concept=concept,
            level=concept_level[concept],
            status=TopicStatus.pending,
            confidence=0.0,
            prerequisites=concept_prereqs.get(concept, []),
        )
        for concept in sorted_concepts
    ]


def build_topic_agenda_from_concepts(
    domain: str,
    target_level: str,
    concept_ids: list[str],
) -> list[AgendaItem]:
    """Build a topic agenda containing only the specified concepts.

    Concepts are topologically sorted (fundamentals first). Only concepts
    present in both the knowledge base AND concept_ids are included.
    """
    full_agenda = build_topic_agenda(domain, target_level)
    concept_set = set(concept_ids)
    return [item for item in full_agenda if item.concept in concept_set]


def get_target_graph_for_concepts(
    domain: str,
    target_level: str,
    concept_ids: list[str],
) -> KnowledgeGraph:
    """Build a KnowledgeGraph containing only the specified concepts.

    Includes edges between selected concepts where prerequisite
    relationships exist. Concepts not in concept_ids are excluded.
    """
    full_graph = get_target_graph(domain, target_level)
    concept_set = set(concept_ids)

    nodes = [n for n in full_graph.nodes if n.concept in concept_set]
    edges = [
        (src, dst) for src, dst in full_graph.edges if src in concept_set and dst in concept_set
    ]

    return KnowledgeGraph(nodes=nodes, edges=edges)


def map_skills_to_domain(skill_ids: list[str]) -> str:
    """Map selected skill IDs to the best-matching knowledge base domain.

    Counts overlap between selected skills and each domain's mapped_skill_ids.
    Returns the domain with the most overlap. Falls back to 'backend_engineering'.
    """
    best_domain = "backend_engineering"
    best_count = 0

    for domain in list_domains():
        try:
            kb = load_knowledge_base(domain)
        except Exception:
            continue
        mapped = set(kb.mapped_skill_ids)
        overlap = len(mapped & set(skill_ids))
        if overlap > best_count:
            best_count = overlap
            best_domain = domain
    return best_domain
