from __future__ import annotations

from fastapi import APIRouter

from api.app.core.feature_registry import get_feature_registry

router = APIRouter(tags=["features"])


@router.get("/v1/features")
def list_features():
    return get_feature_registry()
