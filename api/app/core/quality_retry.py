from __future__ import annotations

from api.app.core.quality_policy import evaluate_quality_gate
from api.app.core.validator import validate
from api.app.core.executor import repair_result

def _run_once(inp, feature: str, reused_pattern, make_plan_fn, execute_feature_fn):
    plan = make_plan_fn(inp, feature)
    result = execute_feature_fn(inp, feature, reused_pattern)
    quality = validate(inp, result)

    if quality.repair_suggested:
        result = repair_result(result)
        quality = validate(inp, result)

    return plan, result, quality

def run_with_quality_retry(
    *,
    inp,
    feature: str,
    reused_pattern,
    make_plan_fn,
    execute_feature_fn,
):
    plan, result, quality = _run_once(inp, feature, reused_pattern, make_plan_fn, execute_feature_fn)
    first_gate = evaluate_quality_gate(feature, quality)

    if first_gate["passed"]:
        return plan, result, quality, {
            "attempts": 1,
            "fallback_used": False,
            "quality_gate": first_gate,
        }

    retry_constraints = dict(inp.constraints or {})
    retry_constraints["quality_mode"] = "strict"
    retry_inp = inp.model_copy(update={"constraints": retry_constraints})

    plan, result, quality = _run_once(retry_inp, feature, reused_pattern, make_plan_fn, execute_feature_fn)
    second_gate = evaluate_quality_gate(feature, quality)

    return plan, result, quality, {
        "attempts": 2,
        "fallback_used": True,
        "first_gate": first_gate,
        "quality_gate": second_gate,
    }
