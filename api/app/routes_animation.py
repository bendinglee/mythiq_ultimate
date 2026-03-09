from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.app.features import animation_feature

router = APIRouter(tags=["animation"])


class AnimationGenerateIn(BaseModel):
    prompt: str = Field(min_length=1)
    goal: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    improve: bool = True


@router.post("/v1/animation/generate")
def animation_generate(inp: AnimationGenerateIn):
    try:
        out = animation_feature.run(inp.model_dump(), reused_pattern=None)

        if hasattr(out, "model_dump"):
            return out.model_dump()

        if isinstance(out, dict):
            return out

        return {
            "ok": True,
            "feature": "animation",
            "type": "markdown",
            "content": str(out),
            "files": [],
            "meta": {},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"animation_generate_failed: {type(e).__name__}: {e}")
