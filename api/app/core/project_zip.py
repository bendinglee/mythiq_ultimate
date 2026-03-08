from __future__ import annotations

from pathlib import Path
import zipfile


def zip_project_bundle(project_id: str) -> dict:
    root = Path("projects") / project_id / "bundle"
    if not root.exists():
        raise FileNotFoundError(f"bundle not found for project_id={project_id}")

    zip_path = root.parent / f"{project_id}_bundle.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fp in sorted(root.rglob("*")):
            if fp.is_file():
                zf.write(fp, arcname=str(fp.relative_to(root.parent)))

    return {
        "project_id": project_id,
        "zip_path": str(zip_path),
        "zip_exists": zip_path.exists(),
        "size_bytes": zip_path.stat().st_size if zip_path.exists() else 0,
    }
