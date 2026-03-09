from __future__ import annotations
from pathlib import Path

from typing import Any, Dict

from api.app.core.artifact_contracts import build_artifact
from api.app.core.image_emitters import emit_image_bundle
from api.app.core.models import FeatureResult, PlanOut, PlanStep
from api.app.core.artifact_store import register_artifact


def plan(inp: Dict[str, Any]) -> PlanOut:
    return PlanOut(
        feature="image",
        steps=[
            PlanStep(id="i1", action="extract_prompt"),
            PlanStep(id="i2", action="build_storyboard"),
            PlanStep(id="i3", action="prepare_render_plan"),
        ],
    )


def run(inp: Dict[str, Any], reused_pattern: str | None = None) -> FeatureResult:
    prompt = inp["prompt"].strip()
    style = "illustration, cinematic lighting, high contrast, rich texture"
    composition = "strong focal subject, dynamic camera angle, clear foreground/background separation"

    content = f"""# Image Blueprint

## Prompt
{prompt}

## Visual Summary
A cinematic image concept based on: {prompt}

## Style
{style}

## Composition
{composition}

## Visual Plan
- strong focal subject
- cinematic lighting
- high contrast composition

## Style Suggestions
- dramatic lighting
- dynamic camera angle
- rich texture

## Pattern
{reused_pattern or "default_image_v1"}
"""

    bundle = emit_image_bundle(prompt, content)

    register_artifact(
        artifact_id=Path(bundle["root"]).parts[1] if len(Path(bundle["root"]).parts) > 1 else Path(bundle["root"]).name,
        feature="image",
        root=bundle["root"],
        files=bundle["files"],
        meta={"pattern_used": reused_pattern or "default"},
    )

    return FeatureResult(
        ok=True,
        feature="image",
        type="markdown",
        content=content,
        files=bundle["files"],
        meta={
            "pattern_used": reused_pattern or "default_image_v1",
            "artifact": {
                **build_artifact("image", content),
                "artifact_data": {
                    **build_artifact("image", content).get("artifact_data", {}),
                    "style": style,
                    "composition": composition,
                    "content": content,
                },
                "next_stage_inputs": {
                    **build_artifact("image", content).get("next_stage_inputs", {}),
                    "visual_summary": f"A cinematic image concept based on: {prompt}",
                    "style": style,
                    "composition": composition,
                },
            },
            "bundle": bundle,
        },
    )
