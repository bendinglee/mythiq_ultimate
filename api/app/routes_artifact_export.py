from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.app.core.artifact_export import export_artifact_zip

router = APIRouter(tags=["artifacts"])


@router.get("/v1/artifacts/export_zip")
def artifacts_export_zip(artifact_id: str):
    try:
        return export_artifact_zip(artifact_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"artifacts_export_zip_failed: {type(e).__name__}: {e}")


@router.get("/v1/artifacts/download_zip/{artifact_id}")
def artifacts_download_zip(artifact_id: str):
    try:
        out = export_artifact_zip(artifact_id)
        return FileResponse(
            out["zip_path"],
            media_type="application/zip",
            filename=f"{artifact_id}.zip",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"artifacts_download_zip_failed: {type(e).__name__}: {e}")
