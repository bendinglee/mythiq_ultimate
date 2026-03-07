from __future__ import annotations

from typing import Dict, List


def plan_project(prompt: str, goal: str | None, detected_feature: str) -> Dict[str, object]:
    stage_map = {
        "text": ["text"],
        "code": ["docs", "code"],
        "game": ["docs", "game", "code"],
        "image": ["docs", "image"],
        "shorts": ["docs", "shorts"],
        "docs": ["docs"],
        "animation": ["docs", "image", "animation"],
    }

    stages = stage_map.get(detected_feature, ["text"])
    return {
        "detected_feature": detected_feature,
        "goal": goal or prompt,
        "stages": stages,
        "deliverables": stages[:],
        "notes": [
            "prefer compact stage briefs",
            "retry weak stages once",
            "preserve project continuity",
        ],
    }


def retry_prompt(original_prompt: str, stage: str, failures: List[str]) -> str:
    fail_text = ", ".join(failures) if failures else "general weakness"
    return (
        f"{original_prompt}\n\n"
        f"Retry instruction for stage '{stage}': improve the output and address: {fail_text}. "
        f"Be more concrete, more structured, and more execution-ready."
    )
