from __future__ import annotations

from typing import Dict, List

from .ledger import best_pattern
from .models import ExecuteIn, RouteOut


KEYWORDS = {
    "code": ["python", "bug", "fix", "script", "api", "backend", "frontend", "fastapi", "debug", "patch", "function"],
    "game": ["game", "phaser", "unity", "level", "enemy", "player", "mechanic", "platformer", "puzzle", "rpg"],
    "text": ["write", "essay", "article", "story", "summary", "outline", "script", "plan", "document"],
    "image": ["image", "poster", "thumbnail", "concept art", "illustration", "cover art", "visual"],
    "shorts": ["short", "shorts", "hook", "viral", "clip", "caption", "cut", "tiktok", "reel"],
}


def _prompt_hint(prompt: str) -> str:
    p = prompt.lower()
    if any(k in p for k in ["python", "bug", "fix", "api", "debug", "script"]):
        return "debug_code"
    if any(k in p for k in ["game", "level", "enemy", "phaser"]):
        return "game_design"
    return "general_text"


def route_execute(inp: ExecuteIn) -> tuple[RouteOut, str | None]:
    prompt = inp.prompt.lower()
    scores: Dict[str, float] = {"text": 0.2, "code": 0.2, "game": 0.2, "image": 0.2, "shorts": 0.2}
    reasons: List[str] = []

    want = (inp.want or "").strip().lower()
    if want in scores:
        scores[want] += 0.5
        reasons.append(f"user_want:{want}")

    for feature, words in KEYWORDS.items():
        hit = sum(1 for w in words if w in prompt)
        if hit:
            scores[feature] += hit * 0.2
            reasons.append(f"keyword_hits:{feature}:{hit}")

    hint = _prompt_hint(inp.prompt)
    reused = None
    for feature in list(scores.keys()):
        bp = best_pattern(feature, hint)
        if bp:
            scores[feature] += min(0.25, float(bp["score"]) * 0.15)

    winner = max(scores, key=scores.get)
    total = sum(max(v, 0.0) for v in scores.values()) or 1.0
    confidence = round(scores[winner] / total, 4)

    bp = best_pattern(winner, hint)
    if bp:
        reused = str(bp["pattern_key"])
        reasons.append(f"reused_pattern:{reused}")

    return (
        RouteOut(
            feature=winner,  # type: ignore[arg-type]
            confidence=confidence,
            reasons=reasons,
            scores={k: round(v, 4) for k, v in scores.items()},
        ),
        reused,
    )
