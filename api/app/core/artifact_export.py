from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import zipfile

PROJECTS = Path("projects")
EXPORTS = PROJECTS / "_exports"


def _artifact_root(artifact_id: str) -> Path:
    root = PROJECTS / artifact_id
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"artifact_not_found: {artifact_id}")
    return root


def export_artifact_zip(artifact_id: str) -> Dict[str, Any]:
    root = _artifact_root(artifact_id)
    EXPORTS.mkdir(parents=True, exist_ok=True)

    zip_path = EXPORTS / f"{artifact_id}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in root.rglob("*"):
            if p.is_file():
                zf.write(p, arcname=str(p.relative_to(root)))

    return {
        "ok": True,
        "artifact_id": artifact_id,
        "root": str(root),
        "zip_path": str(zip_path),
        "download_path": f"/v1/artifacts/download_zip/{artifact_id}",
    }
