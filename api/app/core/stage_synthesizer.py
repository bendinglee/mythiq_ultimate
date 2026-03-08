from __future__ import annotations

from typing import Dict, List

from api.app.core.models import FeatureResult


def synthesize_stage(stage: str, result: FeatureResult) -> Dict[str, object]:
    content = (result.content or "").strip()
    flat = " ".join(content.split())
    short = flat[:280]

    key_points: List[str] = []
    for line in content.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("- "):
            key_points.append(s[2:].strip())
        elif s.startswith("1.") or s.startswith("2.") or s.startswith("3."):
            key_points.append(s)
        if len(key_points) >= 5:
            break

    next_stage_brief = (
        f"Stage={stage}. "
        f"Feature={result.feature}. "
        f"Summary={short}"
    )

    return {
        "summary": short,
        "key_points": key_points,
        "artifacts": {
            "feature": result.feature,
            "type": result.type,
            "files": result.files,
        },
        "next_stage_brief": next_stage_brief,
    }
