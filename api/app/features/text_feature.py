from __future__ import annotations

from typing import Any, Dict

from api.app.core.models import FeatureResult, PlanOut, PlanStep


def plan(inp: Dict[str, Any]) -> PlanOut:
    return PlanOut(
        feature="text",
        steps=[
            PlanStep(id="t1", action="understand_prompt"),
            PlanStep(id="t2", action="draft_structured_response"),
            PlanStep(id="t3", action="format_output"),
        ],
    )


def run(inp: Dict[str, Any], reused_pattern: str | None = None) -> FeatureResult:
    prompt = inp["prompt"].strip()
    goal = (inp.get("goal") or "").strip()

    content = (
        f"# Mythiq Text Output\n\n"
        f"Goal: {goal or 'general completion'}\n\n"
        f"Prompt:\n{prompt}\n\n"
        f"Result:\n"
        f"- clear answer structure\n"
        f"- action-oriented response\n"
        f"- reusable output scaffold\n"
        f"- pattern: {reused_pattern or 'default_text_v1'}\n"
    )

    return FeatureResult(
        ok=True,
        feature="text",
        type="markdown",
        content=content,
        files=[],
        meta={"pattern_used": reused_pattern or "default_text_v1"},
    )
