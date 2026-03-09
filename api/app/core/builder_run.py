from __future__ import annotations

from typing import Any, Dict

from api.app.core.builder_engine import build_project_spec, infer_build_target, render_builder_blueprint, build_builder_plan
from api.app.core.builder_scaffold import emit_builder_scaffold
from api.app.core.models import ProjectRunIn
from api.app.core.project_runner import run_project


def run_builder_project(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = (payload.get("prompt") or "").strip()
    goal = payload.get("goal")
    constraints = payload.get("constraints") or {}
    improve = bool(payload.get("improve", True))
    mode = payload.get("mode") or "project"

    target = infer_build_target(prompt, goal)
    spec = build_project_spec(prompt, goal)
    plan = build_builder_plan(spec)
    blueprint = render_builder_blueprint(spec)

    project_in = ProjectRunIn(
        prompt=prompt,
        goal=goal,
        constraints=constraints,
        mode=mode,
        improve=improve,
        stages=spec["stages"],
    )
    project_out = run_project(project_in)

    scaffold = emit_builder_scaffold(project_out.project_id, spec)

    return {
        "ok": project_out.ok,
        "builder_target": target,
        "project_spec": spec,
        "plan": plan,
        "blueprint": blueprint,
        "project_run": project_out.model_dump(),
        "scaffold": scaffold,
    }
