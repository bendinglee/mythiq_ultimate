from __future__ import annotations

from typing import Any, Dict, List


def assemble_project_output(project_id: str, stages: List[Dict[str, Any]]) -> Dict[str, Any]:
    deliverables = []

    for s in stages:
        route = s.get("route") or {}
        result = s.get("result") or {}
        meta = result.get("meta") or {}
        artifact = meta.get("artifact") or {}

        deliverables.append({
            "stage": s.get("stage"),
            "feature": route.get("feature"),
            "artifact_type": artifact.get("artifact_type"),
            "summary": artifact.get("summary") or " ".join(str(result.get("content", "")).split())[:200],
            "pattern_used": meta.get("pattern_used"),
        })

    final_summary = f"Project {project_id} completed with {len(deliverables)} deliverable(s)."

    return {
        "project_id": project_id,
        "deliverables": deliverables,
        "final_summary": final_summary,
    }
