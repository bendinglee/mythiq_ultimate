from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

from api.app.core.models import ExecuteIn
from api.app.core.executor import execute_feature, make_plan, repair_result
from api.app.core.file_emitters import emit_stage_files
from api.app.core.ledger import new_run_id, save_run
from api.app.core.project_gates import gate_required
from api.app.core.project_resume import build_prior_outputs_from_project, project_has_stage
from api.app.core.project_store import (
    ensure_project,
    append_project_run,
    get_project_state,
    update_project_state,
)
from api.app.core.router import route_execute
from api.app.core.stage_dependencies import missing_dependencies
from api.app.core.stage_synthesizer import synthesize_stage
from api.app.core.validator import validate

router = APIRouter(tags=["project"])


class ProjectRerunIn(BaseModel):
    project_id: str
    stage: str
    prompt: str
    goal: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    improve: bool = True


@router.post("/v1/project/rerun_stage")
def rerun_stage(inp: ProjectRerunIn):
    ensure_project(inp.project_id)

    state = get_project_state(inp.project_id)
    approved = set(state.get("approved_stages") or [])
    already_present = project_has_stage(inp.project_id, inp.stage)

    # stage must either already exist, or be explicitly approved if it is a gated future stage
    if not already_present:
        if gate_required(inp.stage) and inp.stage not in approved:
            raise HTTPException(
                status_code=403,
                detail=f"stage requires approval before rerun: {inp.stage}",
            )

    prior_outputs = build_prior_outputs_from_project(inp.project_id)
    present = [item.get("stage") for item in prior_outputs if item.get("stage")]
    deps_missing = missing_dependencies(inp.stage, present)
    if deps_missing:
        raise HTTPException(
            status_code=409,
            detail=f"missing stage dependencies for {inp.stage}: {', '.join(deps_missing)}",
        )

    lines = [
        f"Base goal: {inp.goal or inp.prompt}",
        f"Original prompt: {inp.prompt}",
        f"Current stage: {inp.stage}",
    ]

    if prior_outputs:
        lines.append("Prior artifact briefs:")
        for item in prior_outputs[-3:]:
            art = item.get("artifact") or {}
            summary = " ".join(str(art.get("summary") or "").split())[:160]
            next_inputs = art.get("next_stage_inputs") or {}
            lines.append(
                f"- {item['stage']} | summary={summary} | next_inputs={next_inputs}"
            )

    payload = ExecuteIn(
        prompt="\n".join(lines),
        goal=inp.goal,
        constraints=inp.constraints,
        mode="project",
        want=inp.stage,
        project_id=inp.project_id,
        improve=inp.improve,
    )

    run_id = new_run_id()
    route, reused_pattern = route_execute(payload)
    plan = make_plan(payload, route.feature)
    result = execute_feature(payload, route.feature, reused_pattern)
    quality = validate(payload, result)

    if quality.repair_suggested:
        result = repair_result(result)
        quality = validate(payload, result)

    synth = synthesize_stage(inp.stage, result)
    artifact = (result.meta or {}).get("artifact") or {}
    emitted = emit_stage_files(inp.project_id, run_id, route.feature, result.model_dump())
    result.files = emitted["files"]

    stage_record = {
        "run_id": run_id,
        "project_id": inp.project_id,
        "stage": inp.stage,
        "route": route.model_dump(),
        "plan": plan.model_dump(),
        "result": result.model_dump(),
        "artifact": artifact,
        "synthesis": synth,
        "quality": quality.model_dump(),
        "reused_pattern": reused_pattern,
        "emitted": emitted,
        "rerun": True,
    }

    save_run(
        run_id=run_id,
        project_id=inp.project_id,
        prompt=payload.prompt,
        goal=payload.goal,
        mode=payload.mode,
        feature=route.feature,
        confidence=route.confidence,
        plan_json=plan.model_dump(),
        result_json=result.model_dump() | {
            "artifact": artifact,
            "synthesis": synth,
            "emitted": emitted,
            "rerun": True,
        },
        quality_json=quality.model_dump(),
        repaired=False,
        latency_ms=0,
    )

    append_project_run(inp.project_id, stage_record)
    update_project_state(
        inp.project_id,
        {
            "history": [{"run_id": run_id, "feature": route.feature, "score": quality.score}],
            "best_patterns": {route.feature: reused_pattern or result.meta.get("pattern_used")},
            "last_completed_stage": inp.stage,
        },
    )

    return {
        "ok": quality.ok,
        "project_id": inp.project_id,
        "run_id": run_id,
        "stage": inp.stage,
        "route": route.model_dump(),
        "plan": plan.model_dump(),
        "result": result.model_dump(),
        "quality": quality.model_dump(),
        "reused_pattern": reused_pattern,
        "rerun": True,
    }
