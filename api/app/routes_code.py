from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.app.features import code_feature

router = APIRouter(tags=["code"])


class CodeGenerateIn(BaseModel):
    prompt: str = Field(min_length=1)
    goal: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    improve: bool = True


@router.post("/v1/code/generate")
def code_generate(inp: CodeGenerateIn):
    try:
        out = code_feature.run(inp.model_dump(), reused_pattern=None)

        if hasattr(out, "model_dump"):
            return out.model_dump()

        if isinstance(out, dict):
            return out

        return {
            "ok": True,
            "feature": "code",
            "type": "python",
            "content": str(out),
            "files": [],
            "meta": {},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"code_generate_failed: {type(e).__name__}: {e}")
