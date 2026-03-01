#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

QDRANT="${QDRANT:-http://127.0.0.1:6333}"
COLL="${COLL:-mythiq_libs}"
API_BASE="${API_BASE:-http://127.0.0.1:7777}"

# ensure collection exists (idempotent; 409 means "already exists")
# also: avoid stale /tmp bodies; treat curl transport errors distinctly
QDRANT="${QDRANT:-http://127.0.0.1:6333}"
COLL="${COLL:-mythiq_libs}"

# wait for qdrant
for i in $(seq 1 60); do
  curl -sS -m 1 "$QDRANT/collections" >/dev/null 2>&1 && break
  sleep 0.25
done

rm -f /tmp/qdrant_create.json

code="$(curl -sS -m 3 -o /tmp/qdrant_create.json -w '%{http_code}' \
  -X PUT "$QDRANT/collections/$COLL" \
  -H 'Content-Type: application/json' \
  -d '{ "vectors": { "size": 768, "distance": "Cosine" } }' || true)"

# code=000 => no HTTP response (connection refused, timeout, DNS, etc.)
if [ "$code" = "000" ]; then
  echo "❌ Qdrant not reachable at $QDRANT (curl transport error). Try: docker compose up -d qdrant" >&2
  exit 1
fi

if [ "$code" != "200" ] && [ "$code" != "201" ] && [ "$code" != "409" ]; then
  echo "❌ Qdrant create collection failed: http=$code body=$(cat /tmp/qdrant_create.json 2>/dev/null || true)" >&2
  exit 1
fi


# helper: route embeddings through API container by calling Ollama from within API code via /v1/execute
# We will call /v1/route only for smoke; embeddings are done by local python below.

PY="$ROOT/.venv/bin/python"
test -x "$PY" || { echo "missing venv python: $PY"; exit 1; }

$PY - <<'PY'
import json, glob, os, requests, math
from pathlib import Path

QDRANT=os.environ.get("QDRANT","http://127.0.0.1:6333")
COLL=os.environ.get("COLL","mythiq_libs")

OLLAMA_BASE=os.environ.get("OLLAMA_BASE","http://127.0.0.1:11434")
EMBED_MODEL=os.environ.get("MYTHIQ_EMBED_MODEL","nomic-embed-text")

def embed(t:str):
    r=requests.post(f"{OLLAMA_BASE}/api/embeddings", json={"model":EMBED_MODEL,"prompt":t}, timeout=30)
    r.raise_for_status()
    v=r.json().get("embedding")
    if not isinstance(v,list) or not v: raise RuntimeError("empty embedding")
    return v

# Qdrant collection vector size must match embedding size
# If mismatch, recreate collection with correct size.
def ensure_coll(dim:int):
    r=requests.get(f"{QDRANT}/collections/{COLL}", timeout=10)
    if r.status_code != 200:
        requests.put(f"{QDRANT}/collections/{COLL}", json={"vectors":{"size":dim,"distance":"Cosine"}}, timeout=10).raise_for_status()
        return
    j=r.json()
    size=j["result"]["config"]["params"]["vectors"]["size"]
    if int(size)!=int(dim):
        requests.delete(f"{QDRANT}/collections/{COLL}", timeout=10).raise_for_status()
        requests.put(f"{QDRANT}/collections/{COLL}", json={"vectors":{"size":dim,"distance":"Cosine"}}, timeout=10).raise_for_status()

paths=glob.glob("libs/*/*.json")
pts=[]
pid=1
for fp in paths:
    data=json.load(open(fp,"r",encoding="utf-8"))
    for row in data:
        tmpl=row["prompt_template"]
        v=embed(tmpl)
        ensure_coll(len(v))
        pts.append({
            "id": pid,
            "vector": v,
            "payload": {
                "lib_id": row["id"],
                "feature": row["feature"],
                "status": row.get("status","active"),
                "quality_score": float(row.get("quality_score",0.5)),
                "prompt_template": tmpl,
                "source_file": str(Path(fp)),
            }
        })
        pid += 1

# upsert
requests.put(
    f"{QDRANT}/collections/{COLL}/points?wait=true",
    json={"points": pts},
    timeout=60,
).raise_for_status()

print(f"INDEXED {len(pts)} patterns into {COLL}")
PY

echo "LIBS_INDEX_OK"
