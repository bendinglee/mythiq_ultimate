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


def update_project_state(project_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    state = load_project_state(project_id) or {
        "project_id": project_id,
        "created_at": time.time(),
        "updated_at": time.time(),
        "goals": [],
        "constraints": {},
        "artifacts": [],
        "history": [],
        "best_patterns": {},
    }
    state["updated_at"] = time.time()
    for k, v in patch.items():
        if isinstance(v, list) and isinstance(state.get(k), list):
            state[k].extend(v)
        elif isinstance(v, dict) and isinstance(state.get(k), dict):
            state[k].update(v)
        else:
            state[k] = v
    save_project_state(project_id, state)
    return state
