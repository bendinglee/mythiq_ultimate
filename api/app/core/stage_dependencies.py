from __future__ import annotations

from typing import Dict, List

DEPENDENCIES: Dict[str, List[str]] = {
    "docs": [],
    "image": ["docs"],
    "animation": ["image"],
    "shorts": ["docs"],
    "code": [],
    "game": ["docs"],
}

def required_stages(stage: str) -> list[str]:
    return list(DEPENDENCIES.get(stage, []))

def missing_dependencies(stage: str, present: list[str]) -> list[str]:
    need = required_stages(stage)
    have = set(present)
    return [s for s in need if s not in have]
