from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.app.features import (
    animation_feature,
    code_feature,
    docs_feature,
    game_feature,
    image_feature,
    shorts_feature,
    text_feature,
)

router = APIRouter(tags=["generate"])


class GenericGenerateIn(BaseModel):
    prompt: str = Field(min_length=1)
    goal: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    improve: bool = True


FEATURE_RUNNERS = {
    "text": text_feature.run,
    "code": code_feature.run,
    "docs": docs_feature.run,
    "shorts": shorts_feature.run,
    "image": image_feature.run,
    "game": game_feature.run,
    "animation": animation_feature.run,
}


@router.post("/v1/generate/{feature}")
def generate_by_feature(feature: str, inp: GenericGenerateIn):
    fn = FEATURE_RUNNERS.get(feature)
    if fn is None:
        raise HTTPException(status_code=404, detail=f"unknown_feature: {feature}")

    try:
        out = fn(inp.model_dump(), reused_pattern=None)

        if hasattr(out, "model_dump"):
            return out.model_dump()

        if isinstance(out, dict):
            return out

        return {
            "ok": True,
            "feature": feature,
            "type": "unknown",
            "content": str(out),
            "files": [],
            "meta": {},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"generate_failed:{feature}: {type(e).__name__}: {e}")
