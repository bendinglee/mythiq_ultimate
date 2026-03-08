from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["export"])


@router.get("/v1/project/export")
def project_export(project_id: str):
    root = Path("projects") / project_id / "bundle"
    manifest = root / "manifest.json"
    summary = root / "README.md"

    if not manifest.exists():
        raise HTTPException(status_code=404, detail=f"bundle not found for project_id={project_id}")

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return {
        "ok": True,
        "project_id": project_id,
        "bundle_dir": str(root),
        "manifest_path": str(manifest),
        "summary_path": str(summary),
        "manifest": payload,
    }
