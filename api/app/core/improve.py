from __future__ import annotations

from api.app.core.ledger import record_pattern
from api.app.core.models import ExecuteIn, FeatureResult, QualityOut


def prompt_hint(prompt: str) -> str:
    p = prompt.lower()
    if any(k in p for k in ["python", "bug", "fix", "api", "debug", "script"]):
        return "debug_code"
    if any(k in p for k in ["game", "level", "enemy", "phaser"]):
        return "game_design"
    return "general_text"


def learn(inp: ExecuteIn, result: FeatureResult, quality: QualityOut, run_id: str) -> None:
    if not quality.ok:
        return
    pattern = str(result.meta.get("pattern_used", f"default_{result.feature}_v1"))
    record_pattern(
        feature=result.feature,
        prompt_hint=prompt_hint(inp.prompt),
        pattern_key=pattern,
        score=float(quality.score),
        run_id=run_id,
    )
