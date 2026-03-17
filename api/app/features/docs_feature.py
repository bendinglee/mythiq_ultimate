from __future__ import annotations
from pathlib import Path

from typing import Any, Dict

from api.app.core.artifact_contracts import build_artifact
from api.app.core.docs_emitters import emit_docs_bundle
from api.app.core.models import FeatureResult, PlanOut, PlanStep
from api.app.core.artifact_store import register_artifact


def plan(inp: Dict[str, Any]) -> PlanOut:
    return PlanOut(
        feature="docs",
        steps=[
            PlanStep(id="d1", action="extract_goal"),
            PlanStep(id="d2", action="structure_sections"),
            PlanStep(id="d3", action="generate_document_blueprint"),
        ],
    )


def run(inp: Dict[str, Any], reused_pattern: str | None = None) -> FeatureResult:
    prompt = inp["prompt"].strip()
    goal = (inp.get("goal") or "produce a strong document").strip()

    content = f"""# Document Blueprint

## Goal
{goal}

## Prompt
{prompt}

## Recommended Structure
1. Title
2. Executive Summary
3. Problem / Opportunity
4. Proposed Direction
5. Execution Plan
6. Risks
7. Next Actions

## Notes
- keep sections scannable
- optimize for practical execution
- pattern: {reused_pattern or "default_docs_v1"}
"""

    bundle = emit_docs_bundle(prompt, content, goal)

    register_artifact(
        artifact_id=Path(bundle["root"]).parts[1] if len(Path(bundle["root"]).parts) > 1 else Path(bundle["root"]).name,
        feature="docs",
        root=bundle["root"],
        files=bundle["files"],
        meta={"pattern_used": reused_pattern or "default"},
    )

    return FeatureResult(
        ok=True,
        feature="docs",
        type="markdown",
        content=content,
        files=bundle["files"],
        meta={
            "pattern_used": reused_pattern or "default_docs_v1",
            "artifact": build_artifact("docs", content),
            "bundle": bundle,
        },
    )
