from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import time

STORE = Path("projects/_meta")
INDEX = STORE / "artifacts.jsonl"


def _ensure() -> None:
    STORE.mkdir(parents=True, exist_ok=True)
    INDEX.touch(exist_ok=True)


def register_artifact(
    artifact_id: str,
    feature: str,
    root: str,
    files: List[str],
    meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    _ensure()
    row = {
        "ts": int(time.time()),
        "artifact_id": artifact_id,
        "feature": feature,
        "root": root,
        "files": files,
        "meta": meta or {},
    }
    with INDEX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def list_registered(limit: int = 200) -> List[Dict[str, Any]]:
    _ensure()
    rows: List[Dict[str, Any]] = []
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    rows.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return rows[:limit]
