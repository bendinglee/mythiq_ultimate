from __future__ import annotations

import time
from typing import List

from api.app.core.artifact_projection import compact_next_inputs
from api.app.core.executor import execute_feature, make_plan, repair_result
from api.app.core.file_emitters import emit_stage_files
from api.app.core.final_assembler import assemble_project_output
from api.app.core.improve import learn
from api.app.core.ledger import new_project_id, new_run_id, save_run
from api.app.core.models import ExecuteIn, ProjectRunIn, ProjectRunOut, ProjectStageOut
from api.app.core.project_bundle import export_project_bundle
from api.app.core.project_gates import build_gate_map
from api.app.core.project_policy import plan_project, retry_prompt
from api.app.core.quality_retry import run_with_quality_retry
from api.app.core.project_store import (
    append_project_run,
    ensure_project,
    get_project_state,
    update_project_state,
)
from api.app.core.router import route_execute
from api.app.core.stage_synthesizer import synthesize_stage
from api.app.core.validator import validate


def _artifact_brief(prior_outputs: List[dict]) -> List[str]:
    out = []
    for item in prior_outputs[-2:]:
        art = item.get("artifact") or {}
        summary = " ".join(str(art.get("summary") or "").split())[:140]
        next_inputs = compact_next_inputs(art)
        out.append(f"{item['stage']} | summary={summary} | next_inputs={next_inputs}")
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

    state = get_project_state(project_id)
    approved_stages = list(state.get("approved_stages") or [])
    gates = build_gate_map(stages, approved_stages)

    update_project_state(
        project_id,
        {
            **state,
            "planned_stages": stages,
            "approved_stages": approved_stages,
            "gates": gates,
        },
    )

    out_stages: List[ProjectStageOut] = []
    prior_outputs: List[dict] = []
    stage_records: List[dict] = []
    blocked_stage = None

    for stage in stages:
        gate = gates.get(stage) or {}
        if gate.get("blocked"):
            blocked_stage = stage
            break

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

        plan, result, quality, quality_retry = run_with_quality_retry(
            inp=payload,
            feature=route.feature,
            reused_pattern=reused_pattern,
            make_plan_fn=make_plan,
            execute_feature_fn=execute_feature,
        )
        repaired = bool(quality_retry.get("attempts", 1) > 1)

        synth = synthesize_stage(stage, result)
        artifact = (result.meta or {}).get("artifact") or {}
        emitted = emit_stage_files(project_id, run_id, route.feature, result.model_dump())
        result.files = emitted["files"]

        stage_record = {
            "run_id": run_id,
            "stage": stage,
            "route": route.model_dump(),
            "plan": plan.model_dump(),
            "result": result.model_dump(),
            "artifact": artifact,
            "synthesis": synth,
            "quality": quality.model_dump(),
            "quality_gate": quality_retry.get("quality_gate", {}),
            "repaired": repaired,
            "reused_pattern": reused_pattern,
            "emitted": emitted,
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
            result_json=result.model_dump() | {
                "synthesis": synth,
                "artifact": artifact,
                "emitted": emitted,
                "quality_gate": quality_retry.get("quality_gate", {}),
            },
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
                "planned_stages": stages,
                "approved_stages": approved_stages,
                "gates": gates,
                "blocked_stage": None,
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
    bundle = export_project_bundle(project_id, final_output, stage_records)

    emitted_total = sum(len((s.result.files or [])) for s in out_stages)

    update_project_state(
        project_id,
        {
            "planned_stages": stages,
            "approved_stages": approved_stages,
            "gates": gates,
            "blocked_stage": blocked_stage,
        },
    )

    metrics = {
        "latency_ms": int((time.time() - started) * 1000),
        "deliverable_count": len(final_output["deliverables"]),
        "bundle_dir": bundle["bundle_dir"],
        "manifest_path": bundle["manifest_path"],
        "summary_path": bundle["summary_path"],
        "emitted_file_count": emitted_total,
        "blocked": blocked_stage is not None,
    }

    summary = final_output["final_summary"]
    if blocked_stage:
        summary += f" Waiting for approval on stage: {blocked_stage}"

    return ProjectRunOut(
        ok=all(s.quality.ok for s in out_stages),
        project_id=project_id,
        stages=out_stages,
        final_summary=summary,
        metrics=metrics,
    )
