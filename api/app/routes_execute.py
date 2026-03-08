from __future__ import annotations

import time

from fastapi import APIRouter

from api.app.core.executor import execute_feature, make_plan
from api.app.core.file_emitters import emit_stage_files
from api.app.core.ledger import new_project_id, new_run_id, save_run
from api.app.core.models import ExecuteIn
from api.app.core.project_store import append_project_run, ensure_project, update_project_state
from api.app.core.reliability import run_reliable
from api.app.core.router import route_execute
from api.app.core.stage_synthesizer import synthesize_stage

router = APIRouter(tags=["execute"])


@router.post("/v1/execute_core")
def execute_v1(inp: ExecuteIn):
    started = time.time()
    project_id = inp.project_id or new_project_id()
    ensure_project(project_id)
    run_id = new_run_id()

    initial_route, _ = route_execute(inp)

    final_feature, plan, result, quality, reliability = run_reliable(
        inp=inp,
        make_plan_fn=make_plan,
        execute_feature_fn=execute_feature,
    )

    final_route, reused_pattern = route_execute(inp.model_copy(update={"want": final_feature}))
    synth = synthesize_stage(final_feature, result)
    artifact = (result.meta or {}).get("artifact") or {}

    emitted = emit_stage_files(project_id, run_id, final_feature, result.model_dump())
    result.files = emitted["files"]

    save_run(
        run_id=run_id,
        project_id=project_id,
        prompt=inp.prompt,
        goal=inp.goal,
        mode=inp.mode,
        feature=final_feature,
        confidence=final_route.confidence,
        plan_json=plan.model_dump(),
        result_json=result.model_dump() | {
            "artifact": artifact,
            "synthesis": synth,
            "reliability": reliability,
            "emitted": emitted,
        },
        quality_json=quality.model_dump(),
        repaired=bool(reliability.get("attempts", 1) > 1),
        latency_ms=int((time.time() - started) * 1000),
    )

    append_project_run(project_id, {
        "run_id": run_id,
        "project_id": project_id,
        "route": final_route.model_dump(),
        "plan": plan.model_dump(),
        "result": result.model_dump(),
        "artifact": artifact,
        "synthesis": synth,
        "quality": quality.model_dump(),
        "reliability": reliability,
        "emitted": emitted,
    })

    update_project_state(
        project_id,
        {
            "history": [{"run_id": run_id, "feature": final_feature, "score": quality.score}],
            "best_patterns": {final_feature: reused_pattern or result.meta.get("pattern_used")},
        },
    )

    return {
        "ok": quality.ok,
        "project_id": project_id,
        "run_id": run_id,
        "route": initial_route.model_dump(),
        "plan": plan.model_dump(),
        "result": result.model_dump(),
        "quality": quality.model_dump(),
        "metrics": {
            "latency_ms": int((time.time() - started) * 1000),
            "emitted_file_count": len(result.files),
        },
        "repaired": bool(reliability.get("attempts", 1) > 1),
        "reused_pattern": reused_pattern,
        "reliability": reliability,
        "quality_gate": reliability.get("quality_gate", {}),
    }
