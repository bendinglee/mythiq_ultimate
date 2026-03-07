from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.app.core.project_store import get_project_state, update_project_state

router = APIRouter(tags=["project"])


class ProjectApproveIn(BaseModel):
    project_id: str
    stage: str


@router.post("/v1/project/approve_stage")
def approve_stage(inp: ProjectApproveIn):
    state = get_project_state(inp.project_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"project not found: {inp.project_id}")

    planned = list(state.get("planned_stages") or [])
    if planned and inp.stage not in planned:
        raise HTTPException(status_code=404, detail=f"stage not planned for project: {inp.stage}")

    approved = list(state.get("approved_stages") or [])
    if inp.stage not in approved:
        approved.append(inp.stage)

    update_project_state(
        inp.project_id,
        {
            "approved_stages": approved,
            "blocked_stage": None,
        },
    )

    return {
        "ok": True,
        "project_id": inp.project_id,
        "stage": inp.stage,               # compatibility alias
        "approved_stage": inp.stage,
        "approved_stages": approved,
    }
