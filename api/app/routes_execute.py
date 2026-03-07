from __future__ import annotations

import time
from fastapi import APIRouter

from api.app.core.executor import execute_feature, make_plan, repair_result
from api.app.core.improve import learn
from api.app.core.ledger import new_project_id, new_run_id, save_run
from api.app.core.models import ExecuteIn, ExecuteOut
from api.app.core.project_store import append_project_run, ensure_project, update_project_state
from api.app.core.router import route_execute
from api.app.core.validator import validate


router = APIRouter(tags=["execute"])


@router.post("/v1/execute_core", response_model=ExecuteOut)
def execute_v1(inp: ExecuteIn) -> ExecuteOut:
    started = time.time()
    run_id = new_run_id()
    project_id = inp.project_id or new_project_id()

    ensure_project(project_id)

    route, reused_pattern = route_execute(inp)
    plan = make_plan(inp, route.feature)
    result = execute_feature(inp, route.feature, reused_pattern)

    quality = validate(inp, result)
    repaired = False
    if inp.improve and quality.repair_suggested:
        result = repair_result(result)
        quality = validate(inp, result)
        repaired = True

    latency_ms = int((time.time() - started) * 1000)

    out = ExecuteOut(
        ok=quality.ok,
        project_id=project_id,
        run_id=run_id,
        route=route,
        plan=plan,
        result=result,
        quality=quality,
        metrics={"latency_ms": latency_ms},
        repaired=repaired,
        reused_pattern=reused_pattern,
    )

    save_run(
        run_id=run_id,
        project_id=project_id,
        prompt=inp.prompt,
        goal=inp.goal,
        mode=inp.mode,
        feature=route.feature,
        confidence=route.confidence,
        plan_json=plan.model_dump(),
        result_json=result.model_dump(),
        quality_json=quality.model_dump(),
        repaired=repaired,
        latency_ms=latency_ms,
    )

    append_project_run(project_id, out.model_dump())
    update_project_state(
        project_id,
        {
            "goals": [inp.goal] if inp.goal else [],
            "constraints": inp.constraints,
            "history": [{"run_id": run_id, "feature": route.feature, "score": quality.score}],
            "best_patterns": {route.feature: reused_pattern or result.meta.get("pattern_used")},
        },
    )

    if inp.improve:
        learn(inp, result, quality, run_id)

    return out
