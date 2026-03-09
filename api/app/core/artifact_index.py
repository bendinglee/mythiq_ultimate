from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

ROOT = Path("projects")


def _detect_feature(path: Path) -> str:
    name = path.name
    for prefix in ("text_", "code_", "docs_", "shorts_", "image_", "game_", "animation_"):
        if name.startswith(prefix):
            return prefix[:-1]
    return "unknown"


def _collect_files(root: Path, limit: int = 12) -> List[str]:
    out: List[str] = []
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out.append(str(p))
            if len(out) >= limit:
                break
    return out


def list_artifacts(limit: int = 50) -> Dict[str, Any]:
    ROOT.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    dirs = [p for p in ROOT.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for p in dirs[:limit]:
        rows.append(
            {
                "artifact_id": p.name,
                "feature": _detect_feature(p),
                "root": str(p),
                "files": _collect_files(p),
            }
        )

    return {
        "ok": True,
        "count": len(rows),
        "artifacts": rows,
    }
