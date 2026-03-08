from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from .ledger import load_project_state, save_project_state


PROJECTS_DIR = Path("projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_project(project_id: str) -> Path:
    p = PROJECTS_DIR / project_id
    (p / "artifacts").mkdir(parents=True, exist_ok=True)
    (p / "runs").mkdir(parents=True, exist_ok=True)
    return p


def append_project_run(project_id: str, run_data: Dict[str, Any]) -> str:
    p = ensure_project(project_id)
    run_path = p / "runs" / f"{run_data['run_id']}.json"
    run_path.write_text(json.dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(run_path)


def update_project_state(project_id: str, state: dict) -> None:
    import json
    from pathlib import Path

    root = Path("projects") / project_id
    root.mkdir(parents=True, exist_ok=True)
    fp = root / "state.json"

    old = {}
    if fp.exists():
        try:
            old = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            old = {}

    merged = dict(old)

    for k, v in state.items():
        if isinstance(v, dict) and isinstance(old.get(k), dict):
            merged[k] = {**old.get(k, {}), **v}
        elif isinstance(v, list) and isinstance(old.get(k), list):
            if k in ("history",):
                merged[k] = old.get(k, []) + v
            else:
                merged[k] = v
        else:
            merged[k] = v

    fp.write_text(json.dumps(merged, indent=2), encoding="utf-8")

def get_project_state(project_id: str) -> dict:
    import json
    from pathlib import Path

    fp = Path("projects") / project_id / "state.json"
    if not fp.exists():
        return {}
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return {}
