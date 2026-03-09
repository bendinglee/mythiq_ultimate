from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.app.features import game_feature

router = APIRouter(tags=["game"])


class GameGenerateIn(BaseModel):
    prompt: str = Field(min_length=1)
    goal: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    improve: bool = True


@router.post("/v1/game/generate")
def game_generate(inp: GameGenerateIn):
    try:
        out = game_feature.run(inp.model_dump(), reused_pattern=None)

        if hasattr(out, "model_dump"):
            return out.model_dump()

        if isinstance(out, dict):
            return out

        return {
            "ok": True,
            "feature": "game",
            "type": "markdown",
            "content": str(out),
            "files": [],
            "meta": {},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"game_generate_failed: {type(e).__name__}: {e}")
