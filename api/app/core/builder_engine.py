from __future__ import annotations

from typing import Any, Dict, List


BUILD_TARGETS = {
    "game": {
        "keywords": ["game", "platformer", "runner", "puzzle", "combat", "rpg", "strategy"],
        "stages": ["docs", "code", "game"],
        "deliverable": "exportable web game scaffold",
    },
    "app": {
        "keywords": ["app", "dashboard", "tool", "website", "web app", "saas", "admin"],
        "stages": ["docs", "code"],
        "deliverable": "working application scaffold",
    },
    "media": {
        "keywords": ["video", "short", "trailer", "animation", "thumbnail", "content", "media"],
        "stages": ["docs", "image", "animation"],
        "deliverable": "media production package",
    },
    "automation": {
        "keywords": ["automation", "workflow", "pipeline", "agent", "builder", "system"],
        "stages": ["docs", "code"],
        "deliverable": "automation service scaffold",
    },
}


def infer_build_target(prompt: str, goal: str | None = None) -> str:
    text = f"{prompt}\n{goal or ''}".lower()
    scores: Dict[str, int] = {}

    for target, cfg in BUILD_TARGETS.items():
        score = 0
        for kw in cfg["keywords"]:
            if kw in text:
                score += 1
        scores[target] = score

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "app"


def build_project_spec(prompt: str, goal: str | None = None) -> Dict[str, Any]:
    target = infer_build_target(prompt, goal)
    cfg = BUILD_TARGETS[target]

    return {
        "target": target,
        "title": _make_title(prompt),
        "prompt": prompt,
        "goal": goal or "",
        "stages": list(cfg["stages"]),
        "deliverable": cfg["deliverable"],
        "quality_contract": [
            "must be concrete",
            "must be exportable",
            "must be reusable",
            "must include next actions",
        ],
    }


def build_builder_plan(spec: Dict[str, Any]) -> Dict[str, Any]:
    stages: List[str] = [str(x) for x in spec["stages"]]

    return {
        "feature": str(spec["target"]),
        "steps": [
            {"id": "b1", "action": "infer_project_type", "meta": {"target": str(spec["target"])}},
            {"id": "b2", "action": "build_project_spec", "meta": {"title": str(spec["title"])}},
            {"id": "b3", "action": "emit_stage_plan", "meta": {"stage_count": str(len(stages)), "stage_list": ",".join(stages)}},
            {"id": "b4", "action": "prepare_execution_contract", "meta": {"deliverable": str(spec["deliverable"])}},
        ],
    }


def render_builder_blueprint(spec: Dict[str, Any]) -> str:
    stages = "\n".join(f"- {x}" for x in spec["stages"])
    qc = "\n".join(f"- {x}" for x in spec["quality_contract"])

    return f"""# Builder Engine Blueprint

## Project Title
{spec["title"]}

## Target
{spec["target"]}

## Prompt
{spec["prompt"]}

## Goal
{spec["goal"] or "Not provided"}

## Planned Stages
{stages}

## Expected Deliverable
{spec["deliverable"]}

## Quality Contract
{qc}

## Execution Notes
- route prompt into the correct builder path
- generate stage outputs in sequence
- keep outputs structured and exportable
- preserve reusable project artifacts
"""


def _make_title(prompt: str) -> str:
    words = [w.strip(".,:;!?") for w in prompt.split() if w.strip()]
    words = words[:8] or ["Mythiq", "Builder", "Project"]
    return " ".join(w.capitalize() for w in words)
