from __future__ import annotations

from typing import Any, Dict

from api.app.core.models import FeatureResult, PlanOut, PlanStep


def plan(inp: Dict[str, Any]) -> PlanOut:
    return PlanOut(
        feature="shorts",
        steps=[
            PlanStep(id="s1", action="find_hook"),
            PlanStep(id="s2", action="define_beat_structure"),
            PlanStep(id="s3", action="generate_edit_script"),
        ],
    )


def run(inp: Dict[str, Any], reused_pattern: str | None = None) -> FeatureResult:
    prompt = inp["prompt"].strip()

    content = f"""# Shorts Blueprint

## Topic
{prompt}

## Hook (0-3s)
Open with the strongest curiosity gap or emotional claim.

## Beat Structure
1. Hook
2. Context
3. Escalation
4. Payoff
5. CTA / loop

## Edit Notes
- fast cuts
- subtitle-first delivery
- motion every 1-2 seconds
- visual resets every beat
- music swell before payoff

## Output Package
- short script
- caption rhythm
- cut notes
- scene prompt ideas

## Pattern
{reused_pattern or "default_shorts_v1"}
"""

    return FeatureResult(
        ok=True,
        feature="shorts",
        type="markdown",
        content=content,
        files=[],
        meta={"pattern_used": reused_pattern or "default_shorts_v1"},
    )
