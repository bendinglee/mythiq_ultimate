from __future__ import annotations

from typing import Any, Dict

MIN_SCORE_BY_FEATURE: Dict[str, float] = {
    "text": 0.85,
    "docs": 0.90,
    "code": 0.90,
    "game": 0.90,
    "image": 0.90,
    "shorts": 0.90,
    "animation": 0.90,
}

REQUIRED_CHECKS_BY_FEATURE: Dict[str, list[str]] = {
    "text": ["valid", "complete", "format_ok", "useful_length", "artifact_present"],
    "docs": [
        "valid", "complete", "format_ok", "useful_length",
        "artifact_present", "artifact_data_present", "next_stage_inputs_present",
        "docs_has_headings", "docs_has_key_points", "docs_has_summary_input",
    ],
    "code": [
        "valid", "complete", "format_ok", "useful_length",
        "artifact_present", "artifact_data_present", "next_stage_inputs_present",
        "code_has_language", "code_has_functions", "code_has_summary_input",
    ],
    "game": [
        "valid", "complete", "format_ok", "useful_length",
        "artifact_present", "artifact_data_present", "next_stage_inputs_present",
    ],
    "image": [
        "valid", "complete", "format_ok", "useful_length",
        "artifact_present", "artifact_data_present", "next_stage_inputs_present",
        "image_has_style", "image_has_composition", "image_has_visual_summary",
    ],
    "shorts": [
        "valid", "complete", "format_ok", "useful_length",
        "artifact_present", "artifact_data_present", "next_stage_inputs_present",
    ],
    "animation": [
        "valid", "complete", "format_ok", "useful_length",
        "artifact_present", "artifact_data_present", "next_stage_inputs_present",
        "animation_has_shots", "animation_has_notes", "animation_has_handoff",
    ],
}

def evaluate_quality_gate(feature: str, quality: Any) -> dict:
    checks = dict(getattr(quality, "checks", {}) or {})
    failures = list(getattr(quality, "failures", []) or [])
    score = float(getattr(quality, "score", 0.0) or 0.0)

    min_score = MIN_SCORE_BY_FEATURE.get(feature or "text", 0.85)
    required = REQUIRED_CHECKS_BY_FEATURE.get(feature or "text", ["valid", "complete"])
    missing_required = [k for k in required if not checks.get(k, False)]
    score_ok = score >= min_score
    passed = score_ok and not missing_required and not failures

    return {
        "passed": passed,
        "feature": feature,
        "score": score,
        "min_score": min_score,
        "score_ok": score_ok,
        "required_checks": required,
        "missing_required_checks": missing_required,
        "failures": failures,
    }
