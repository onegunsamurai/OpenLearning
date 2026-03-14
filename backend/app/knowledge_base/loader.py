from __future__ import annotations

from pathlib import Path

import yaml

from app.graph.state import BloomLevel, KnowledgeGraph, KnowledgeNode
from app.knowledge_base.schema import LEVEL_ORDER, KnowledgeBaseSchema

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
