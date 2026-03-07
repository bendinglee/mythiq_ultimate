from __future__ import annotations

from .models import ExecuteIn, FeatureResult, QualityOut


def validate(inp: ExecuteIn, result: FeatureResult) -> QualityOut:
    failures: list[str] = []
    checks = {
        "valid": bool(result.ok),
        "complete": bool(result.content.strip()),
        "format_ok": bool(result.type.strip()),
        "useful_length": len(result.content.strip()) >= 40,
    }

    if not checks["valid"]:
        failures.append("result_not_ok")
    if not checks["complete"]:
        failures.append("empty_content")
    if not checks["format_ok"]:
        failures.append("missing_type")
    if not checks["useful_length"]:
        failures.append("content_too_short")

    score = 1.0
    if failures:
        score -= 0.2 * len(failures)
    score = max(0.0, min(1.0, score))

    return QualityOut(
        ok=not failures,
        score=round(score, 4),
        checks=checks,
        failures=failures,
        repair_suggested=bool(failures),
    )
