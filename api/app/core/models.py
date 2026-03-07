from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


FeatureName = Literal["text", "code", "game", "image", "shorts"]


class ExecuteIn(BaseModel):
    prompt: str = Field(..., min_length=1)
    goal: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    mode: str = Field(default="single")
    want: Optional[str] = None
    project_id: Optional[str] = None
    max_steps: int = Field(default=4, ge=1, le=20)
    improve: bool = True


class RouteOut(BaseModel):
    feature: FeatureName
    confidence: float
    reasons: List[str] = Field(default_factory=list)
    scores: Dict[str, float] = Field(default_factory=dict)


class PlanStep(BaseModel):
    id: str
    action: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class PlanOut(BaseModel):
    feature: FeatureName
    steps: List[PlanStep] = Field(default_factory=list)


class FeatureResult(BaseModel):
    ok: bool
    feature: FeatureName
    type: str
    content: str = ""
    files: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class QualityOut(BaseModel):
    ok: bool
    score: float
    checks: Dict[str, bool] = Field(default_factory=dict)
    failures: List[str] = Field(default_factory=list)
    repair_suggested: bool = False


class ExecuteOut(BaseModel):
    ok: bool
    project_id: str
    run_id: str
    route: RouteOut
    plan: PlanOut
    result: FeatureResult
    quality: QualityOut
    metrics: Dict[str, Any] = Field(default_factory=dict)
    repaired: bool = False
    reused_pattern: Optional[str] = None
