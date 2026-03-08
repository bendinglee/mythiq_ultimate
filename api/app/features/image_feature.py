from __future__ import annotations

from typing import Any, Dict

from api.app.core.artifact_contracts import build_artifact
from api.app.core.models import FeatureResult, PlanOut, PlanStep


def plan(inp: Dict[str, Any]) -> PlanOut:
    return PlanOut(
        feature="image",
        steps=[
            PlanStep(id="i1", action="extract_visual_subject", meta={}),
            PlanStep(id="i2", action="define_style_and_composition", meta={}),
            PlanStep(id="i3", action="package_prompt_negative_and_thumbnail_notes", meta={}),
        ],
    )


def run(inp: Dict[str, Any], reused_pattern: str | None = None) -> FeatureResult:
    prompt = (inp.get("prompt") or "").strip()
    style = inp.get("constraints", {}).get("style", "cinematic stylized")

    content = f"""# Image Generation Package

## User Prompt
{prompt}

## Visual Intent
- subject clarity
- strong silhouette
- readable composition
- high-impact focal point
- thumbnail readability at small size

## Style
- {style}
- non-photoreal by default
- production-ready prompt scaffold

## Primary Prompt
Subject: {prompt}
Style: {style}
Lighting: dramatic readable lighting
Composition: centered focal subject with depth
Camera: medium-wide heroic framing
Quality: highly detailed stylized concept art
Mood: epic, high contrast, emotionally charged

## Negative Prompt
- blurry details
- unreadable composition
- muddy lighting
- low contrast
- extra limbs
- distorted hands
- cluttered background
- tiny focal subject

## Thumbnail Notes
- keep one dominant focal point
- preserve title-safe negative space
- prioritize contrast around face/object
- avoid overfilling frame edges

## Pattern
{reused_pattern or "default_image_v2"}
"""

    return FeatureResult(
        ok=True,
        feature="image",
        type="markdown",
        content=content,
        files=[],
        meta={
            "pattern_used": reused_pattern or "default_image_v2",
            "artifact": build_artifact("image", content),
        },
    )
