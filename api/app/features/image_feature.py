from __future__ import annotations

from typing import Any, Dict

from api.app.core.models import FeatureResult, PlanOut, PlanStep


def plan(inp: Dict[str, Any]) -> PlanOut:
    return PlanOut(
        feature="image",
        steps=[
            PlanStep(id="i1", action="extract_visual_subject"),
            PlanStep(id="i2", action="define_style_and_composition"),
            PlanStep(id="i3", action="produce_image_prompt_package"),
        ],
    )


def run(inp: Dict[str, Any], reused_pattern: str | None = None) -> FeatureResult:
    prompt = inp["prompt"].strip()
    style = inp.get("constraints", {}).get("style", "cinematic stylized")

    content = f"""# Image Generation Package

## User Prompt
{prompt}

## Visual Intent
- subject clarity
- strong silhouette
- readable composition
- high-impact focal point

## Style
- {style}
- non-photoreal by default
- production-ready prompt scaffold

## Prompt Package
Subject: {prompt}
Style: {style}
Lighting: dramatic readable lighting
Composition: centered focal subject with depth
Quality: highly detailed stylized concept art

## Pattern
{reused_pattern or "default_image_v1"}
"""

    return FeatureResult(
        ok=True,
        feature="image",
        type="markdown",
        content=content,
        files=[],
        meta={"pattern_used": reused_pattern or "default_image_v1"},
    )
