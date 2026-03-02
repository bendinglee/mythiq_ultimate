from __future__ import annotations

import os
import math
import requests
from typing import List

OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://ollama:11434")
EMBED_MODEL = os.environ.get("MYTHIQ_EMBED_MODEL", "nomic-embed-text")

def _norm(v: List[float]) -> float:
    return math.sqrt(sum(x*x for x in v)) or 1.0

def cosine(a: List[float], b: List[float]) -> float:
    na = _norm(a)
    nb = _norm(b)
    return sum(x*y for x,y in zip(a,b)) / (na * nb)

def embed_text(text: str) -> List[float]:
    t = (text or "").strip()
    if not t:
        return [0.0]

    base = OLLAMA_BASE.rstrip("/")
    mdl = EMBED_MODEL

    # Endpoint reality check:
    # Many installs expose /api/embeddings (prompt->embedding).
    # Some expose /api/embed (input->embeddings).
    # We try embeddings first, then embed.
    j = None

    # 1) Try /api/embeddings (most common)
    try:
        r = requests.post(
            f"{base}/api/embeddings",
            json={"model": mdl, "prompt": t},
            timeout=30,
        )
        if r.status_code != 404:
            r.raise_for_status()
            j = r.json()
    except Exception as e:
        # only continue to next endpoint if this looks like "endpoint missing"
        if j is None:
            pass
        else:
            raise RuntimeError(f"ollama embeddings failed: {e}")

    # 2) Fallback: /api/embed
    if j is None:
        try:
            r = requests.post(
                f"{base}/api/embed",
                json={"model": mdl, "input": t},
                timeout=30,
            )
            r.raise_for_status()
            j = r.json()
        except Exception as e:
            raise RuntimeError(f"ollama embed failed: {e}")

    # Old shape: {"embedding": [...]}
    if isinstance(j, dict) and isinstance(j.get("embedding"), list) and j["embedding"]:
        return [float(x) for x in j["embedding"]]

    # New shape: {"embeddings": [[...], ...]}
    if isinstance(j, dict) and "embeddings" in j and isinstance(j["embeddings"], list) and j["embeddings"]:
        v0 = j["embeddings"][0]
        if isinstance(v0, list) and v0:
            return [float(x) for x in v0]

    raise RuntimeError(f"Ollama returned empty/unknown embedding shape: {type(j)} keys={list(j.keys()) if isinstance(j, dict) else None}")
