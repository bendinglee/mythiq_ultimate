from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _project_root(project_id: str) -> Path:
    return Path("projects") / project_id


def load_project_stage_records(project_id: str) -> List[Dict[str, Any]]:
    root = _project_root(project_id) / "runs"
    if not root.exists():
        return []

    rows: List[Dict[str, Any]] = []
    for fp in sorted(root.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def latest_stage_map(project_id: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in load_project_stage_records(project_id):
        stage = row.get("stage")
        if stage:
            out[stage] = row
    return out


def build_prior_outputs_from_project(project_id: str) -> List[Dict[str, Any]]:
    priors: List[Dict[str, Any]] = []
    for row in load_project_stage_records(project_id):
        stage = row.get("stage")
        artifact = row.get("artifact") or ((row.get("result") or {}).get("meta") or {}).get("artifact") or {}
        if stage:
            priors.append({
                "stage": stage,
                "artifact": artifact,
            })
    return priors


def project_has_stage(project_id: str, stage: str) -> bool:
    return stage in latest_stage_map(project_id)


def load_stage_record(project_id: str, stage: str) -> Dict[str, Any] | None:
    return latest_stage_map(project_id).get(stage)
