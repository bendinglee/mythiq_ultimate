from __future__ import annotations

from api.app.core.models import ExecuteIn, FeatureResult, PlanOut
from api.app.features import (
    animation_feature,
    code_feature,
    docs_feature,
    game_feature,
    image_feature,
    shorts_feature,
    text_feature,
)


def make_plan(inp: ExecuteIn, feature: str) -> PlanOut:
    if feature == "code":
        return code_feature.plan(inp.model_dump())
    if feature == "game":
        return game_feature.plan(inp.model_dump())
    if feature == "image":
        return image_feature.plan(inp.model_dump())
    if feature == "shorts":
        return shorts_feature.plan(inp.model_dump())
    if feature == "docs":
        return docs_feature.plan(inp.model_dump())
    if feature == "animation":
        return animation_feature.plan(inp.model_dump())
    return text_feature.plan(inp.model_dump())


def execute_feature(inp: ExecuteIn, feature: str, reused_pattern: str | None = None) -> FeatureResult:
    if feature == "code":
        return code_feature.run(inp.model_dump(), reused_pattern)
    if feature == "game":
        return game_feature.run(inp.model_dump(), reused_pattern)
    if feature == "image":
        return image_feature.run(inp.model_dump(), reused_pattern)
    if feature == "shorts":
        return shorts_feature.run(inp.model_dump(), reused_pattern)
    if feature == "docs":
        return docs_feature.run(inp.model_dump(), reused_pattern)
    if feature == "animation":
        return animation_feature.run(inp.model_dump(), reused_pattern)
    return text_feature.run(inp.model_dump(), reused_pattern)


def repair_result(result: FeatureResult) -> FeatureResult:
    if result.content.strip():
        return result
    result.content = "Repair applied: generated fallback content."
    result.meta["repair_applied"] = True
    result.ok = True
    return result
