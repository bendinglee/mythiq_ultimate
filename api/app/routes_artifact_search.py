from __future__ import annotations

from fastapi import APIRouter, Query

from api.app.core.artifact_index import list_artifacts

router = APIRouter(tags=["artifacts"])


def _rows():
    data = list_artifacts(limit=10000)
    if isinstance(data, dict):
        return data.get("artifacts") or []
    if isinstance(data, list):
        return data
    return []


@router.get("/v1/artifacts/search")
def artifact_search(
    feature: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    rows = _rows()

    if feature:
        rows = [r for r in rows if isinstance(r, dict) and r.get("feature") == feature]

    if q:
        ql = q.lower()
        rows = [
            r for r in rows
            if isinstance(r, dict)
            and (
                ql in (r.get("artifact_id") or "").lower()
                or ql in (r.get("root") or "").lower()
            )
        ]

    return {"ok": True, "count": len(rows[:limit]), "artifacts": rows[:limit]}


@router.get("/v1/artifacts/latest")
def artifact_latest(
    feature: str = Query(...),
):
    rows = _rows()

    for r in rows:
        if isinstance(r, dict) and r.get("feature") == feature:
            return {"ok": True, "artifact": r}

    return {"ok": False, "artifact": None}
