from __future__ import annotations

from fastapi import APIRouter

from api.app.core.models import ProjectRunIn, ProjectRunOut
from api.app.core.project_runner import run_project

router = APIRouter(tags=["project"])


@router.post("/v1/project/run", response_model=ProjectRunOut)
def project_run_v1(inp: ProjectRunIn) -> ProjectRunOut:
    return run_project(inp)
