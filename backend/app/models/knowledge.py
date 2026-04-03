from __future__ import annotations

from app.models.base import CamelModel
from app.models.bloom import BloomLevel


class KnowledgeNode(CamelModel):
    concept: str
    confidence: float  # 0.0-1.0
    bloom_level: BloomLevel
    prerequisites: list[str] = []
    evidence: list[str] = []


class KnowledgeGraph(CamelModel):
    nodes: list[KnowledgeNode] = []
    edges: list[tuple[str, str]] = []  # (prerequisite, dependent)

    def get_node(self, concept: str) -> KnowledgeNode | None:
        for node in self.nodes:
            if node.concept == concept:
                return node
        return None

    def upsert_node(self, node: KnowledgeNode) -> None:
        for i, existing in enumerate(self.nodes):
            if existing.concept == node.concept:
                self.nodes[i] = node
                return
        self.nodes.append(node)
