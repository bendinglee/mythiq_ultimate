from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.app.core.artifact_index import list_artifacts

router = APIRouter(tags=["artifacts"])


@router.get("/v1/artifacts/detail")
def artifact_detail(
    artifact_id: str = Query(..., min_length=1),
):
    try:
        data = list_artifacts(limit=10000)

        if isinstance(data, dict):
            rows = data.get("artifacts") or []
        elif isinstance(data, list):
            rows = data
        else:
            rows = []

        for row in rows:
            if isinstance(row, dict) and row.get("artifact_id") == artifact_id:
                return {"ok": True, "artifact": row}

        raise HTTPException(status_code=404, detail=f"artifact_not_found: {artifact_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"artifact_detail_failed: {type(e).__name__}: {e}",
        )
