from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.app.core.project_gates import build_gate_map
from api.app.core.project_resume import load_project_stage_records, latest_stage_map
from api.app.core.project_store import get_project_state

router = APIRouter(tags=["project"])


@router.get("/v1/project/status")
def project_status(project_id: str):
    rows = load_project_stage_records(project_id)
    state = get_project_state(project_id)

    if not rows and not state:
        raise HTTPException(status_code=404, detail=f"project not found: {project_id}")

    latest = latest_stage_map(project_id)
    planned = list(state.get("planned_stages") or [])
    approved = list(state.get("approved_stages") or [])
    gates = build_gate_map(planned, approved) if planned else {}

    blocked_stage = None
    for stage in planned:
        g = gates.get(stage) or {}
        if g.get("blocked") and stage not in latest:
            blocked_stage = stage
            break

    return {
        "ok": True,
        "project_id": project_id,
        "run_count": len(rows),
        "stages_present": list(latest.keys()),
        "planned_stages": planned,
        "approved_stages": approved,
        "blocked_stage": blocked_stage,
        "gates": gates,
        "latest_stage_runs": {
            k: {
                "run_id": v.get("run_id"),
                "feature": (v.get("route") or {}).get("feature"),
                "quality_ok": (v.get("quality") or {}).get("ok"),
            }
            for k, v in latest.items()
        },
    }
