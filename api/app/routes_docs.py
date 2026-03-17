from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.app.features import docs_feature

router = APIRouter(tags=["docs"])


class DocsGenerateIn(BaseModel):
    prompt: str = Field(min_length=1)
    goal: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    improve: bool = True


@router.post("/v1/docs/generate")
def docs_generate(inp: DocsGenerateIn):
    try:
        out = docs_feature.run(inp.model_dump(), reused_pattern=None)

        if hasattr(out, "model_dump"):
            return out.model_dump()

        if isinstance(out, dict):
            return out

        return {
            "ok": True,
            "feature": "docs",
            "type": "markdown",
            "content": str(out),
            "files": [],
            "meta": {},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"docs_generate_failed: {type(e).__name__}: {e}")
