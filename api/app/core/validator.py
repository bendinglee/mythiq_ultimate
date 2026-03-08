from __future__ import annotations

from typing import Dict

from api.app.core.models import ExecuteIn, FeatureResult, QualityOut


def _basic_checks(result: FeatureResult) -> Dict[str, bool]:
    text = (result.content or "").strip()
    return {
        "valid": bool(text),
        "complete": len(text) >= 80,
        "format_ok": result.type in ("markdown", "python", "json", "text"),
        "useful_length": len(text.split()) >= 12,
    }


def _artifact_checks(result: FeatureResult) -> Dict[str, bool]:
    art = (result.meta or {}).get("artifact") or {}
    artifact_type = art.get("artifact_type")
    artifact_data = art.get("artifact_data") or {}
    next_stage_inputs = art.get("next_stage_inputs") or {}

    return {
        "artifact_present": bool(artifact_type),
        "artifact_data_present": isinstance(artifact_data, dict) and bool(artifact_data),
        "next_stage_inputs_present": isinstance(next_stage_inputs, dict) and bool(next_stage_inputs),
    }


def _feature_specific_checks(result: FeatureResult) -> Dict[str, bool]:
    art = (result.meta or {}).get("artifact") or {}
    data = art.get("artifact_data") or {}
    nxt = art.get("next_stage_inputs") or {}
    feature = result.feature

    checks: Dict[str, bool] = {}

    if feature == "code":
        checks.update({
            "code_has_language": data.get("language") == "python",
            "code_has_functions": isinstance(data.get("functions"), list) and len(data.get("functions", [])) >= 1,
            "code_has_summary_input": bool(nxt.get("code_summary")),
        })
    elif feature == "game":
        checks.update({
            "game_has_systems": isinstance(data.get("systems"), list) and len(data.get("systems", [])) >= 3,
            "game_has_summary_input": bool(nxt.get("game_summary")),
        })
    elif feature == "docs":
        checks.update({
            "docs_has_headings": isinstance(data.get("headings"), list) and len(data.get("headings", [])) >= 3,
            "docs_has_key_points": isinstance(data.get("key_points"), list) and len(data.get("key_points", [])) >= 2,
            "docs_has_summary_input": bool(nxt.get("doc_summary")),
        })
    elif feature == "image":
        checks.update({
            "image_has_style": bool(data.get("style")),
            "image_has_composition": bool(data.get("composition")),
            "image_has_visual_summary": bool(nxt.get("visual_summary")),
        })
    elif feature == "shorts":
        checks.update({
            "shorts_has_beats": isinstance(data.get("beats"), list) and len(data.get("beats", [])) >= 3,
            "shorts_has_edit_notes": isinstance(data.get("edit_notes"), list) and len(data.get("edit_notes", [])) >= 2,
            "shorts_has_handoff": bool(nxt.get("hook_and_beats")),
        })
    elif feature == "animation":
        checks.update({
            "animation_has_shots": isinstance(data.get("shot_list"), list) and len(data.get("shot_list", [])) >= 3,
            "animation_has_notes": isinstance(data.get("notes"), list) and len(data.get("notes", [])) >= 2,
            "animation_has_handoff": bool(nxt.get("shot_summary")),
        })
    else:
        checks.update({
            "text_has_brief": bool(nxt.get("brief")),
        })

    return checks


def validate(inp: ExecuteIn, result: FeatureResult) -> QualityOut:
    checks = {}
    checks.update(_basic_checks(result))
    checks.update(_artifact_checks(result))
    checks.update(_feature_specific_checks(result))

    failures = [k for k, ok in checks.items() if not ok]
    score = round(sum(1 for v in checks.values() if v) / max(1, len(checks)), 4)

    ok = score >= 0.80
    repair_suggested = score < 0.98

    return QualityOut(
        ok=ok,
        score=score,
        checks=checks,
        failures=failures,
        repair_suggested=repair_suggested,
    )
