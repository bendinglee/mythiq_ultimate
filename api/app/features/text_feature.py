from __future__ import annotations
from pathlib import Path

from typing import Any, Dict

from api.app.core.artifact_contracts import build_artifact
from api.app.core.text_emitters import emit_text_bundle
from api.app.core.models import FeatureResult, PlanOut, PlanStep
from api.app.core.artifact_store import register_artifact


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

    register_artifact(
        artifact_id=Path(bundle["root"]).parts[1] if len(Path(bundle["root"]).parts) > 1 else Path(bundle["root"]).name,
        feature="text",
        root=bundle["root"],
        files=bundle["files"],
        meta={"pattern_used": reused_pattern or "default"},
    )

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
