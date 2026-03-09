from __future__ import annotations

from typing import Any, Dict

from api.app.core.artifact_contracts import build_artifact
from api.app.core.game_emitters import emit_game_bundle
from api.app.core.models import FeatureResult, PlanOut, PlanStep


def plan(inp: Dict[str, Any]) -> PlanOut:
    return PlanOut(
        feature="game",
        steps=[
            PlanStep(id="g1", action="extract_core_loop"),
            PlanStep(id="g2", action="define_mechanics"),
            PlanStep(id="g3", action="define_progression_and_assets"),
        ],
    )


def run(inp: Dict[str, Any], reused_pattern: str | None = None) -> FeatureResult:
    prompt = inp["prompt"].strip()

    content = f"""# Game Design Skeleton

## Prompt
{prompt}

## Core Loop
- player action
- system response
- reward/progression
- repeat with increasing mastery

## Systems
- movement
- objective
- fail state
- scoring
- upgrade path

## Build Notes
- exportable web build
- lightweight assets first
- pattern: {reused_pattern or "default_game_v1"}
"""

    bundle = emit_game_bundle(prompt, content)

    return FeatureResult(
        ok=True,
        feature="game",
        type="markdown",
        content=content,
        files=bundle["files"],
        meta={
            "pattern_used": reused_pattern or "default_game_v1",
            "artifact": build_artifact("game", content),
            "bundle": bundle,
        },
    )
