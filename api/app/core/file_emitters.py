from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def _write_json(path: Path, data: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


def emit_stage_files(project_id: str, run_id: str, feature: str, result: Dict[str, Any]) -> Dict[str, Any]:
    root = Path("projects") / project_id / "generated" / feature / run_id
    meta = result.get("meta") or {}
    artifact = meta.get("artifact") or {}
    content = result.get("content", "")

    out: Dict[str, Any] = {
        "feature": feature,
        "root": str(root),
        "files": [],
    }

    if feature == "code":
        py_path = root / "main.py"
        out["files"].append(_write_text(py_path, content))

    elif feature == "game":
        md_path = root / "game_design.md"
        artifact_path = root / "game_design.json"
        out["files"].append(_write_text(md_path, content))
        out["files"].append(_write_json(artifact_path, artifact))

    elif feature == "docs":
        md_path = root / "document_blueprint.md"
        artifact_path = root / "document_blueprint.json"
        out["files"].append(_write_text(md_path, content))
        out["files"].append(_write_json(artifact_path, artifact))

    elif feature == "image":
        md_path = root / "image_prompt_package.md"
        artifact_path = root / "image_prompt_package.json"
        out["files"].append(_write_text(md_path, content))
        out["files"].append(_write_json(artifact_path, artifact))

    elif feature == "shorts":
        md_path = root / "shorts_blueprint.md"
        artifact_path = root / "shorts_blueprint.json"
        out["files"].append(_write_text(md_path, content))
        out["files"].append(_write_json(artifact_path, artifact))

    elif feature == "animation":
        md_path = root / "animation_plan.md"
        artifact_path = root / "animation_plan.json"
        out["files"].append(_write_text(md_path, content))
        out["files"].append(_write_json(artifact_path, artifact))

    else:
        md_path = root / "output.md"
        artifact_path = root / "output.json"
        out["files"].append(_write_text(md_path, content))
        out["files"].append(_write_json(artifact_path, artifact))

    return out
