from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .embeddings import embed_text, cosine

@dataclass(frozen=True)
class RouteResult:
    feature: str
    confidence: float
    secondary: List[Tuple[str, float]]
    needs_clarify: bool
    clarify_question: str

# Minimal feature set for now; expand as pipelines land
FEATURE_EXEMPLARS: Dict[str, List[str]] = {
    "text": [
        "write an explanation", "summarize this", "rewrite this", "brainstorm ideas", "answer a question",
    ],
    "code": [
        "write python code", "fix this bug", "refactor this", "unit tests", "fastapi endpoint",
    ],
    "games": [
        "make a phaser game", "build a browser game", "match-3 game", "platformer prototype",
    ],
    "shorts": [
        "turn video into shorts", "viral hook", "captioned clips", "edit highlights",
    ],
    "docs": [
        "write a document", "create a report", "proposal", "whitepaper",
    ],
    "slides": [
        "make a powerpoint", "slide deck", "presentation outline",
    ],
    "images": [
        "generate an image", "stable diffusion prompt", "comfyui workflow",
    ],
    "animation": [
        "storyboard", "animate scenes", "shot list", "video interpolation",
    ],
}

def _feature_vector(feature: str) -> List[float]:
    # Embed all exemplars and average (cheap + deterministic for small lists)
    vecs = [embed_text(x) for x in FEATURE_EXEMPLARS[feature]]
    n = len(vecs)
    if n == 1:
        return vecs[0]
    # average
    d = len(vecs[0])
    out = [0.0] * d
    for v in vecs:
        for i, x in enumerate(v):
            out[i] += float(x)
    return [x / n for x in out]

# Precompute vectors lazily (so importing doesn't hard-fail if embeddings not available yet)
_CACHE: Dict[str, List[float]] = {}

def _get_vec(feature: str) -> List[float]:
    v = _CACHE.get(feature)
    if v is not None:
        return v
    v = _feature_vector(feature)
    _CACHE[feature] = v
    return v

def route(prompt: str, clarify_threshold: float = 0.75) -> RouteResult:
    qv = embed_text(prompt)

    scored: List[Tuple[str, float]] = []
    for f in FEATURE_EXEMPLARS.keys():
        fv = _get_vec(f)
        scored.append((f, float(cosine(qv, fv))))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_f, top_s = scored[0]
    secondary = scored[1:3]

    # Multi-feature hint if runner-up is close
    multi = False
    if secondary:
        f2, s2 = secondary[0]
        multi = (top_s - s2) < 0.05 and s2 > 0.70

    needs_clarify = (top_s < clarify_threshold) or multi

    clarify = ""
    if needs_clarify:
        if multi and secondary:
            clarify = f"I can do both {top_f} and {secondary[0][0]}. Which one should I prioritize?"
        else:
            clarify = "What output do you want: text, code, game, shorts, docs, slides, images, or animation?"

    return RouteResult(
        feature=top_f,
        confidence=top_s,
        secondary=secondary,
        needs_clarify=needs_clarify,
        clarify_question=clarify,
    )
