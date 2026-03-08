from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.app.core.project_zip import zip_project_bundle

router = APIRouter(tags=["export"])


@router.get("/v1/project/export_zip")
def project_export_zip(project_id: str):
    try:
        out = zip_project_bundle(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "ok": True,
        "project_id": project_id,
        "zip_path": out["zip_path"],
        "size_bytes": out["size_bytes"],
    }


@router.get("/v1/project/download_zip")
def project_download_zip(project_id: str):
    try:
        out = zip_project_bundle(project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return FileResponse(
        out["zip_path"],
        media_type="application/zip",
        filename=f"{project_id}_bundle.zip",
    )
