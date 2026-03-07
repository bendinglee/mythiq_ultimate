from __future__ import annotations

import time
from typing import List

from api.app.core.artifact_projection import compact_next_inputs
from api.app.core.executor import execute_feature, make_plan, repair_result
from api.app.core.final_assembler import assemble_project_output
from api.app.core.improve import learn
from api.app.core.ledger import new_project_id, new_run_id, save_run
from api.app.core.models import ExecuteIn, ProjectRunIn, ProjectRunOut, ProjectStageOut
from api.app.core.project_policy import plan_project, retry_prompt
from api.app.core.project_store import append_project_run, ensure_project, update_project_state
from api.app.core.router import route_execute
from api.app.core.stage_synthesizer import synthesize_stage
from api.app.core.validator import validate


def _artifact_brief(prior_outputs: List[dict]) -> List[str]:
    out = []
    for item in prior_outputs[-2:]:
        art = item.get("artifact") or {}
        summary = " ".join(str(art.get("summary") or "").split())[:140]
        next_inputs = compact_next_inputs(art)
        out.append(
            f"{item['stage']} | summary={summary} | next_inputs={next_inputs}"
        )
    return out


def _stage_prompt(base_prompt: str, goal: str | None, prior_outputs: List[dict], stage: str) -> str:
    lines = [
        f"Base goal: {goal or base_prompt}",
        f"Original prompt: {base_prompt}",
        f"Current stage: {stage}",
    ]
    briefs = _artifact_brief(prior_outputs)
    if briefs:
        lines.append("Prior artifact briefs:")
        for b in briefs:
            lines.append(f"- {b}")
    return "\n".join(lines)


def run_project(inp: ProjectRunIn) -> ProjectRunOut:
    started = time.time()
    project_id = inp.project_id or new_project_id()
    ensure_project(project_id)

    initial = ExecuteIn(
        prompt=inp.prompt,
        goal=inp.goal,
        constraints=inp.constraints,
        mode=inp.mode,
        want=None,
        project_id=project_id,
        improve=inp.improve,
    )

    first_route, _ = route_execute(initial)
    project_plan = plan_project(inp.prompt, inp.goal, first_route.feature)
    stages = inp.stages or list(project_plan["stages"])

    out_stages: List[ProjectStageOut] = []
    prior_outputs: List[dict] = []
    stage_records: List[dict] = []

    for stage in stages:
        run_id = new_run_id()
        stage_prompt = _stage_prompt(inp.prompt, inp.goal, prior_outputs, stage)

        payload = ExecuteIn(
            prompt=stage_prompt,
            goal=inp.goal,
            constraints=inp.constraints,
            mode="project",
            want=stage,
            project_id=project_id,
            improve=inp.improve,
        )

        route, reused_pattern = route_execute(payload)
        plan = make_plan(payload, route.feature)
        result = execute_feature(payload, route.feature, reused_pattern)

        quality = validate(payload, result)
        repaired = False

        if quality.repair_suggested:
            retry_payload = ExecuteIn(
                prompt=retry_prompt(stage_prompt, stage, quality.failures),
                goal=inp.goal,
                constraints=inp.constraints,
                mode="project",
                want=stage,
                project_id=project_id,
                improve=inp.improve,
            )
            retry_route, retry_reused = route_execute(retry_payload)
            retry_plan = make_plan(retry_payload, retry_route.feature)
            retry_result = execute_feature(retry_payload, retry_route.feature, retry_reused)
            retry_quality = validate(retry_payload, retry_result)

            if retry_quality.score >= quality.score:
                route, reused_pattern, plan, result, quality = (
                    retry_route, retry_reused, retry_plan, retry_result, retry_quality
                )
                repaired = True

        if quality.repair_suggested and not repaired:
            result = repair_result(result)
            quality = validate(payload, result)

        synth = synthesize_stage(stage, result)
        artifact = (result.meta or {}).get("artifact") or {}

        stage_record = {
            "run_id": run_id,
            "stage": stage,
            "route": route.model_dump(),
            "plan": plan.model_dump(),
            "result": result.model_dump(),
            "artifact": artifact,
            "synthesis": synth,
            "quality": quality.model_dump(),
            "repaired": repaired,
            "reused_pattern": reused_pattern,
        }
        stage_records.append(stage_record)

        save_run(
            run_id=run_id,
            project_id=project_id,
            prompt=payload.prompt,
            goal=payload.goal,
            mode=payload.mode,
            feature=route.feature,
            confidence=route.confidence,
            plan_json=plan.model_dump() | {"project_plan": project_plan},
            result_json=result.model_dump() | {"synthesis": synth, "artifact": artifact},
            quality_json=quality.model_dump(),
            repaired=repaired,
            latency_ms=0,
        )

        append_project_run(project_id, {
            "project_id": project_id,
            "project_plan": project_plan,
            **stage_record,
        })

        update_project_state(
            project_id,
            {
                "history": [{"run_id": run_id, "feature": route.feature, "score": quality.score}],
                "best_patterns": {route.feature: reused_pattern or result.meta.get("pattern_used")},
            },
        )

        if inp.improve:
            learn(payload, result, quality, run_id)

        out_stages.append(
            ProjectStageOut(
                stage=stage,
                route=route,
                plan=plan,
                result=result,
                quality=quality,
            )
        )

        prior_outputs.append({
            "stage": stage,
            "artifact": artifact,
        })

    final_output = assemble_project_output(project_id, stage_records)

    return ProjectRunOut(
        ok=all(s.quality.ok for s in out_stages),
        project_id=project_id,
        stages=out_stages,
        final_summary=final_output["final_summary"],
        metrics={
            "latency_ms": int((time.time() - started) * 1000),
            "deliverable_count": len(final_output["deliverables"]),
        },
    )
