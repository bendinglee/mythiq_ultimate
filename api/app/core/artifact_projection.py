from __future__ import annotations

from typing import Any, Dict, List


def compact_next_inputs(artifact: Dict[str, Any]) -> Dict[str, Any]:
    nsi = (artifact or {}).get("next_stage_inputs") or {}
    out: Dict[str, Any] = {}

    for k, v in nsi.items():
        if isinstance(v, str):
            out[k] = " ".join(v.split())[:180]
        elif isinstance(v, list):
            cleaned: List[str] = []
            for item in v[:5]:
                cleaned.append(" ".join(str(item).split())[:120])
            out[k] = cleaned
        elif isinstance(v, dict):
            tmp = {}
            for kk, vv in list(v.items())[:5]:
                tmp[str(kk)] = " ".join(str(vv).split())[:120]
            out[k] = tmp
        else:
            out[k] = v

    return out
