from __future__ import annotations

from typing import Any, Dict

from api.app.core.artifact_contracts import build_artifact
from api.app.core.text_emitters import emit_text_bundle
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
    goal = (inp.get("goal") or "respond clearly").strip()

    content = f"""# Mythiq Text Output

Goal: {goal}

Prompt:
{prompt}

Result:
- clear answer structure
- action-oriented response
- reusable output scaffold
- pattern: {reused_pattern or "default_text_v1"}
"""

    bundle = emit_text_bundle(prompt, content)

    return FeatureResult(
        ok=True,
        feature="text",
        type="markdown",
        content=content,
        files=bundle["files"],
        meta={
            "pattern_used": reused_pattern or "default_text_v1",
            "artifact": build_artifact("text", content),
            "bundle": bundle,
        },
    )
