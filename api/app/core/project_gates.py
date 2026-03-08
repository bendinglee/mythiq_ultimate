from __future__ import annotations

from typing import Dict, Any, List

DEFAULT_GATE_STAGES = {"image", "animation", "game"}


def gate_required(stage: str) -> bool:
    return stage in DEFAULT_GATE_STAGES


def build_gate_map(stages: List[str], approved_stages: List[str] | None = None) -> Dict[str, Dict[str, Any]]:
    approved = set(approved_stages or [])
    out: Dict[str, Dict[str, Any]] = {}
    for stage in stages:
        needs = gate_required(stage)
        out[stage] = {
            "stage": stage,
            "requires_approval": needs,
            "approved": (stage in approved) if needs else True,
            "blocked": needs and stage not in approved,
        }
    return out


def first_blocked_stage(stages: List[str], approved_stages: List[str] | None = None) -> str | None:
    gates = build_gate_map(stages, approved_stages)
    for stage in stages:
        if gates[stage]["blocked"]:
            return stage
    return None


def approve_stage_in_state(state: Dict[str, Any], stage: str) -> Dict[str, Any]:
    approved = list(state.get("approved_stages") or [])
    if stage not in approved:
        approved.append(stage)
    state["approved_stages"] = approved
    return state
