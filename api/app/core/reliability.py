from __future__ import annotations

from api.app.core.router import route_execute
from api.app.core.quality_retry import run_with_quality_retry

def run_reliable(*, inp, make_plan_fn, execute_feature_fn):
    route, reused_pattern = route_execute(inp)
    final_feature = route.feature

    plan, result, quality, quality_report = run_with_quality_retry(
        inp=inp,
        feature=final_feature,
        reused_pattern=reused_pattern,
        make_plan_fn=make_plan_fn,
        execute_feature_fn=execute_feature_fn,
    )

    reliability = {
        "attempts": int(quality_report.get("attempts", 1)),
        "fallback_used": bool(quality_report.get("fallback_used", False)),
        "final_feature": final_feature,
        "tried_features": [final_feature],
        "reused_pattern": reused_pattern,
        "quality_gate": quality_report.get("quality_gate", {}),
    }

    if "first_gate" in quality_report:
        reliability["first_gate"] = quality_report["first_gate"]

    return final_feature, plan, result, quality, reliability
