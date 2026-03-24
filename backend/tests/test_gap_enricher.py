"""Tests for gap_enricher pure functions: _compute_priority, _compute_overall_readiness."""

from __future__ import annotations

from app.agents.gap_enricher import _compute_overall_readiness, _compute_priority
from app.graph.state import BloomLevel, KnowledgeNode


def _node(concept: str, confidence: float) -> KnowledgeNode:
    """Shorthand helper to build a KnowledgeNode with minimal fields."""
    return KnowledgeNode(
        concept=concept,
        confidence=confidence,
        bloom_level=BloomLevel.understand,
        prerequisites=[],
        evidence=[],
    )


class TestComputePriority:
    """Tests for _compute_priority(current_confidence, target_confidence)."""

    def test_critical_when_gap_above_0_6(self):
        # gap = 1.0 - 0.3 = 0.7 > 0.6
        assert _compute_priority(0.3, 1.0) == "critical"

    def test_high_when_gap_above_0_4(self):
        # gap = 0.9 - 0.4 = 0.5 > 0.4
        assert _compute_priority(0.4, 0.9) == "high"

    def test_medium_when_gap_above_0_2(self):
        # gap = 0.6 - 0.3 = 0.3 > 0.2
        assert _compute_priority(0.3, 0.6) == "medium"

    def test_low_when_gap_at_or_below_0_2(self):
        # gap = 0.3 - 0.2 = 0.1 <= 0.2
        assert _compute_priority(0.2, 0.3) == "low"

    # ── Boundary tests ──

    def test_boundary_exactly_0_6_gap_is_not_critical(self):
        # gap = 0.6 exactly → NOT > 0.6, so falls to "high"
        assert _compute_priority(0.0, 0.6) == "high"

    def test_boundary_just_above_0_6_gap_is_critical(self):
        assert _compute_priority(0.0, 0.61) == "critical"

    def test_boundary_exactly_0_4_gap_is_not_high(self):
        # gap = 0.4 exactly → NOT > 0.4, so falls to "medium"
        assert _compute_priority(0.0, 0.4) == "medium"

    def test_boundary_just_above_0_4_gap_is_high(self):
        assert _compute_priority(0.0, 0.41) == "high"

    def test_boundary_exactly_0_2_gap_is_not_medium(self):
        # gap = 0.2 exactly → NOT > 0.2, so falls to "low"
        assert _compute_priority(0.0, 0.2) == "low"

    def test_boundary_just_above_0_2_gap_is_medium(self):
        assert _compute_priority(0.0, 0.21) == "medium"

    # ── Edge cases ──

    def test_negative_gap_returns_low(self):
        # current > target → gap is negative
        assert _compute_priority(0.9, 0.2) == "low"

    def test_zero_gap_returns_low(self):
        assert _compute_priority(0.5, 0.5) == "low"

    def test_max_gap_returns_critical(self):
        # gap = 1.0 - 0.0 = 1.0
        assert _compute_priority(0.0, 1.0) == "critical"


class TestComputeOverallReadiness:
    """Tests for _compute_overall_readiness(current_nodes, target_nodes)."""

    def test_empty_target_nodes_returns_100(self):
        current = [_node("a", 0.5)]
        assert _compute_overall_readiness(current, []) == 100

    def test_both_empty_returns_100(self):
        assert _compute_overall_readiness([], []) == 100

    def test_all_nodes_at_target_returns_100(self):
        current = [_node("a", 0.8), _node("b", 0.6)]
        target = [_node("a", 0.8), _node("b", 0.6)]
        assert _compute_overall_readiness(current, target) == 100

    def test_all_nodes_at_zero_returns_0(self):
        current = [_node("a", 0.0), _node("b", 0.0)]
        target = [_node("a", 0.8), _node("b", 0.6)]
        assert _compute_overall_readiness(current, target) == 0

    def test_mixed_values(self):
        current = [_node("a", 0.4), _node("b", 0.3)]
        target = [_node("a", 0.8), _node("b", 0.6)]
        # a: 0.4/0.8 = 0.5, b: 0.3/0.6 = 0.5 → avg = 0.5 → 50
        assert _compute_overall_readiness(current, target) == 50

    def test_current_exceeds_target_capped_at_1(self):
        current = [_node("a", 1.0)]
        target = [_node("a", 0.5)]
        # min(1.0/0.5, 1.0) = 1.0 → 100
        assert _compute_overall_readiness(current, target) == 100

    def test_zero_target_confidence_skipped(self):
        current = [_node("a", 0.5), _node("b", 0.4)]
        target = [_node("a", 0.0), _node("b", 0.8)]
        # a has target_conf=0.0, skipped; b: 0.4/0.8 = 0.5 → 50
        assert _compute_overall_readiness(current, target) == 50

    def test_all_zero_target_confidence_returns_0(self):
        current = [_node("a", 0.5)]
        target = [_node("a", 0.0)]
        # All targets have 0 confidence → count=0 → returns 0
        assert _compute_overall_readiness(current, target) == 0

    def test_missing_current_node_treated_as_zero(self):
        # Target has "b" but current doesn't → current_conf = 0.0
        current = [_node("a", 0.8)]
        target = [_node("a", 0.8), _node("b", 0.8)]
        # a: 0.8/0.8 = 1.0, b: 0.0/0.8 = 0.0 → avg = 0.5 → 50
        assert _compute_overall_readiness(current, target) == 50

    def test_single_node_partial(self):
        current = [_node("a", 0.6)]
        target = [_node("a", 0.8)]
        # 0.6/0.8 = 0.7499... → int() truncates to 74
        assert _compute_overall_readiness(current, target) == 74

    def test_result_is_int(self):
        current = [_node("a", 0.33)]
        target = [_node("a", 1.0)]
        result = _compute_overall_readiness(current, target)
        assert isinstance(result, int)
        assert result == 33  # int(0.33 * 100)
