from __future__ import annotations
from pathlib import Path

from typing import Any, Dict

from api.app.core.artifact_contracts import build_artifact
from api.app.core.animation_emitters import emit_animation_bundle
from api.app.core.models import FeatureResult, PlanOut, PlanStep
from api.app.core.artifact_store import register_artifact


def plan(inp: Dict[str, Any]) -> PlanOut:
    return PlanOut(
        feature="animation",
        steps=[
            PlanStep(id="a1", action="extract_scene_goal"),
            PlanStep(id="a2", action="define_shot_sequence"),
            PlanStep(id="a3", action="generate_animation_plan"),
        ],
    )


def run(inp: Dict[str, Any], reused_pattern: str | None = None) -> FeatureResult:
    prompt = inp["prompt"].strip()

    content = f"""# Animation Shot Plan

## Prompt
{prompt}

## Shot Flow
1. Establishing shot
2. Subject introduction
3. Motion escalation
4. Close-up emphasis
5. Payoff frame

## Production Notes
- visual continuity first
- shot-to-shot clarity
- simple camera motion before complexity
- keep asset reuse high

## Deliverables
- shot list
- scene beat notes
- animation prompt package

## Pattern
{reused_pattern or "default_animation_v1"}
"""

    bundle = emit_animation_bundle(prompt, content)

    register_artifact(
        artifact_id=Path(bundle["root"]).parts[1] if len(Path(bundle["root"]).parts) > 1 else Path(bundle["root"]).name,
        feature="animation",
        root=bundle["root"],
        files=bundle["files"],
        meta={"pattern_used": reused_pattern or "default"},
    )

    return FeatureResult(
        ok=True,
        feature="animation",
        type="markdown",
        content=content,
        files=bundle["files"],
        meta={
            "pattern_used": reused_pattern or "default_animation_v1",
            "artifact": build_artifact("animation", content),
            "bundle": bundle,
        },
    )
