from __future__ import annotations
from pathlib import Path

from typing import Any, Dict, List

from api.app.core.artifact_contracts import build_artifact
from api.app.core.shorts_emitters import emit_shorts_bundle
from api.app.core.models import FeatureResult, PlanOut, PlanStep
from api.app.core.artifact_store import register_artifact


def _pick_topic(payload: Dict[str, Any]) -> str:
    return (
        payload.get("prompt")
        or payload.get("goal")
        or "Create a high-retention short"
    )


def _hook_variants(topic: str) -> List[str]:
    return [
        f"You were told the wrong story about {topic}.",
        f"This is the moment {topic} changed everything.",
        f"Almost nobody realizes what really happened in {topic}.",
    ]


def plan(payload: Dict[str, Any]) -> PlanOut:
    return PlanOut(
        feature="shorts",
        steps=[
            PlanStep(id="s1", action="find_hook", meta={}),
            PlanStep(id="s2", action="build_beat_timeline", meta={}),
            PlanStep(id="s3", action="package_edit_blueprint", meta={}),
        ],
    )


def run(payload: Dict[str, Any], reused_pattern: str | None = None) -> FeatureResult:
    topic = _pick_topic(payload)
    hooks = _hook_variants(topic)

    content = f"""# Shorts Blueprint

## Topic
{topic}

## Hook Variants
1. {hooks[0]}
2. {hooks[1]}
3. {hooks[2]}

## Timestamped Beat Plan
- 0-2s: Hook
- 2-6s: Context
- 6-12s: Escalation
- 12-18s: Payoff
- 18-22s: Loop / CTA

## Caption Style
- subtitle-first
- high contrast
- short phrase chunks
- emphasis word in caps sparingly

## Edit Notes
- open with biggest claim immediately
- captions on every spoken beat
- hard visual change every 1-2 seconds
- zoom or motion accent on key words
- music swell before payoff
- end on a line that loops back into the hook

## CTA / Loop Ending
- ask a curiosity question
- imply there is one more hidden detail
- make the last line connect back to the first line

## Pattern
{reused_pattern or "default_shorts_v2"}
"""

    bundle = emit_shorts_bundle(topic, content)

    register_artifact(
        artifact_id=Path(bundle["root"]).parts[1] if len(Path(bundle["root"]).parts) > 1 else Path(bundle["root"]).name,
        feature="shorts",
        root=bundle["root"],
        files=bundle["files"],
        meta={"pattern_used": reused_pattern or "default"},
    )

    return FeatureResult(
        ok=True,
        feature="shorts",
        type="markdown",
        content=content,
        files=bundle["files"],
        meta={
            "pattern_used": reused_pattern or "default_shorts_v2",
            "artifact": build_artifact("shorts", content),
            "bundle": bundle,
        },
    )
