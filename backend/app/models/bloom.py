from __future__ import annotations

from enum import StrEnum


class BloomLevel(StrEnum):
    remember = "remember"
    understand = "understand"
    apply = "apply"
    analyze = "analyze"
    evaluate = "evaluate"
    create = "create"


BLOOM_ORDER: list[BloomLevel] = list(BloomLevel)

LEVEL_BLOOM_MAP: dict[str, BloomLevel] = {
    "junior": BloomLevel.understand,
    "mid": BloomLevel.apply,
    "senior": BloomLevel.analyze,
    "staff": BloomLevel.evaluate,
}


def bloom_index(level: BloomLevel) -> int:
    return BLOOM_ORDER.index(level)
