from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _safe_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_markdown_summary(project_id: str, payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Mythiq Project Bundle")
    lines.append("")
    lines.append(f"- Project ID: `{project_id}`")
    lines.append(f"- Final Summary: {payload.get('final_summary', '')}")
    lines.append("")

    for d in payload.get("deliverables", []):
        lines.append(f"## Stage: {d.get('stage')}")
        lines.append(f"- Feature: {d.get('feature')}")
        lines.append(f"- Artifact Type: {d.get('artifact_type')}")
        lines.append(f"- Pattern Used: {d.get('pattern_used')}")
        lines.append(f"- Summary: {d.get('summary')}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def export_project_bundle(project_id: str, final_output: Dict[str, Any], stage_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    root = Path("projects") / project_id / "bundle"
    artifacts_dir = root / "artifacts"

    manifest = {
        "project_id": project_id,
        "final_output": final_output,
        "deliverable_count": len(final_output.get("deliverables", [])),
        "stages": [],
    }

    for idx, record in enumerate(stage_records, start=1):
        stage = record.get("stage", f"stage_{idx}")
        route = record.get("route", {})
        result = record.get("result", {})
        artifact = record.get("artifact", {})
        quality = record.get("quality", {})

        stage_slug = f"{idx:02d}_{stage}"
        stage_json_path = artifacts_dir / f"{stage_slug}.json"
        stage_md_path = artifacts_dir / f"{stage_slug}.md"

        stage_payload = {
            "stage": stage,
            "route": route,
            "result": result,
            "artifact": artifact,
            "quality": quality,
        }
        _safe_write_json(stage_json_path, stage_payload)
        _safe_write_text(stage_md_path, str(result.get("content", "")))

        manifest["stages"].append({
            "stage": stage,
            "feature": route.get("feature"),
            "artifact_type": artifact.get("artifact_type"),
            "json_path": str(stage_json_path),
            "markdown_path": str(stage_md_path),
        })

    manifest_path = root / "manifest.json"
    summary_path = root / "README.md"

    _safe_write_json(manifest_path, manifest)
    _safe_write_text(summary_path, build_markdown_summary(project_id, final_output))

    return {
        "bundle_dir": str(root),
        "manifest_path": str(manifest_path),
        "summary_path": str(summary_path),
        "deliverable_count": len(final_output.get("deliverables", [])),
    }
