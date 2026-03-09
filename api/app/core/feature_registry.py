from __future__ import annotations

from typing import Any, Dict, List


FEATURE_REGISTRY: List[Dict[str, Any]] = [
    {"feature": "text", "generate_path": "/v1/text/generate", "type": "markdown"},
    {"feature": "code", "generate_path": "/v1/code/generate", "type": "python"},
    {"feature": "docs", "generate_path": "/v1/docs/generate", "type": "markdown"},
    {"feature": "shorts", "generate_path": "/v1/shorts/generate", "type": "markdown"},
    {"feature": "image", "generate_path": "/v1/image/generate", "type": "markdown"},
    {"feature": "game", "generate_path": "/v1/game/generate", "type": "markdown"},
    {"feature": "animation", "generate_path": "/v1/animation/generate", "type": "markdown"},
]


def get_feature_registry() -> Dict[str, Any]:
    return {
        "ok": True,
        "count": len(FEATURE_REGISTRY),
        "features": FEATURE_REGISTRY,
    }
