from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.app.core.artifact_index import list_artifacts

router = APIRouter(tags=["artifacts"])


@router.get("/v1/artifacts")
def artifacts(limit: int = 50):
    try:
        return list_artifacts(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"artifacts_failed: {type(e).__name__}: {e}")
