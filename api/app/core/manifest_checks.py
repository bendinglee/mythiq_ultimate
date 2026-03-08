from __future__ import annotations

from typing import Any, Dict, List


REQUIRED_TOP = ["project_id", "deliverable_count", "stages"]
REQUIRED_FINAL = ["project_id", "deliverables", "final_summary"]
REQUIRED_STAGE = ["stage", "feature", "artifact_type", "json_path", "markdown_path"]


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _normalize_final_output(manifest: Dict[str, Any]) -> Dict[str, Any]:
    # New format
    if isinstance(manifest.get("final_output"), dict):
        return manifest["final_output"]

    # Legacy fixture format
    deliverables = manifest.get("deliverables")
    final_summary = manifest.get("final_summary")

    if isinstance(deliverables, list) or isinstance(final_summary, str):
        return {
            "project_id": manifest.get("project_id"),
            "deliverables": deliverables or [],
            "final_summary": final_summary or "",
        }

    return {}


def validate_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    failures: List[str] = []

    for key in REQUIRED_TOP:
        if key not in manifest:
            failures.append(f"missing_top:{key}")

    final_output = _normalize_final_output(manifest)
    for key in REQUIRED_FINAL:
        if key not in final_output:
            failures.append(f"missing_final:{key}")

    stages = manifest.get("stages")
    if not isinstance(stages, list) or not stages:
        failures.append("stages_missing_or_empty")
    else:
        for i, stage in enumerate(stages, start=1):
            for key in REQUIRED_STAGE:
                if key not in stage:
                    failures.append(f"missing_stage:{i}:{key}")
            for key in ("stage", "feature", "artifact_type", "json_path", "markdown_path"):
                if key in stage and not _is_nonempty_str(stage[key]):
                    failures.append(f"bad_stage_value:{i}:{key}")

    deliverables = final_output.get("deliverables") or []
    if not isinstance(deliverables, list) or not deliverables:
        failures.append("deliverables_missing_or_empty")

    deliverable_count = manifest.get("deliverable_count")
    if not isinstance(deliverable_count, int) or deliverable_count < 1:
        failures.append("bad_deliverable_count")
    elif isinstance(deliverables, list) and deliverable_count != len(deliverables):
        failures.append("deliverable_count_mismatch")

    if "project_id" in final_output and final_output.get("project_id") != manifest.get("project_id"):
        failures.append("project_id_mismatch")

    if "final_summary" in final_output and not _is_nonempty_str(final_output.get("final_summary")):
        failures.append("bad_final_summary")

    ok = not failures
    return {
        "ok": ok,
        "failures": failures,
    }
