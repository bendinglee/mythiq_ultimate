from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.app.core.builder_engine import build_builder_plan, build_project_spec, render_builder_blueprint
from api.app.core.builder_run import run_builder_project

router = APIRouter(tags=["builder"])


class BuilderPlanIn(BaseModel):
    prompt: str
    goal: Optional[str] = None
    mode: str = "project"
    improve: bool = True


@router.post("/v1/builder/plan")
def builder_plan(inp: BuilderPlanIn):
    try:
        spec = build_project_spec(inp.prompt, inp.goal)
        plan = build_builder_plan(spec)
        blueprint = render_builder_blueprint(spec)

        return {
            "ok": True,
            "builder_target": spec["target"],
            "project_spec": spec,
            "plan": plan,
            "blueprint": blueprint,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"builder_plan_failed: {type(e).__name__}: {e}")

@router.post("/v1/builder/run")
def builder_run(inp: BuilderPlanIn):
    try:
        return run_builder_project(inp.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"builder_run_failed: {type(e).__name__}: {e}")
