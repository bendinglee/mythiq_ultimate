#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

QDRANT="${QDRANT:-http://127.0.0.1:6333}"
COLL="${COLL:-mythiq_libs}"
OLLAMA="${OLLAMA:-http://127.0.0.1:11434}"
EMBED_MODEL="${MYTHIQ_EMBED_MODEL:-nomic-embed-text}"
PROMPT="${1:-make a fastapi endpoint that returns json health check}"

# Prefer project venv python; fall back to python3
PY="./.venv/bin/python"
if [ ! -x "$PY" ]; then
  PY="$(command -v python3 || true)"
fi
test -n "${PY:-}" || { echo "❌ missing python3 and .venv/bin/python" >&2; exit 1; }

# Ensure deps up
curl -fsS -m 2 "$OLLAMA/api/tags" >/dev/null
curl -fsS -m 2 "$QDRANT/collections" >/dev/null

# Ensure libs indexed (quiet)
./scripts/index_libs_qdrant.sh >/dev/null

TMP_REQ="$(mktemp -t mythiq_embed_req.XXXXXX.json)"
TMP_EMB="$(mktemp -t mythiq_embed_res.XXXXXX.json)"
TMP_QRY="$(mktemp -t mythiq_qdrant_qry.XXXXXX.json)"
TMP_QRES="$(mktemp -t mythiq_qdrant_res.XXXXXX.json)"
TMP_COLL="$(mktemp -t mythiq_qdrant_coll.XXXXXX.json)"
trap 'rm -f "$TMP_REQ" "$TMP_EMB" "$TMP_QRY" "$TMP_QRES" "$TMP_COLL"' EXIT

# 1) Build embedding request JSON (safe)
EMBED_MODEL="$EMBED_MODEL" PROMPT="$PROMPT" "$PY" - <<'PY' >"$TMP_REQ"
import json, os
print(json.dumps({"model": os.environ["EMBED_MODEL"], "prompt": os.environ["PROMPT"]}))
PY

# 2) Call Ollama embeddings (capture body + http code)
ecode="$(curl -sS -m 60 -o "$TMP_EMB" -w '%{http_code}' \
  "$OLLAMA/api/embeddings" \
  -H 'Content-Type: application/json' \
  --data-binary @"$TMP_REQ" || true)"

if [ "$ecode" = "000" ]; then
  echo "❌ Ollama not reachable at $OLLAMA" >&2
  exit 1
fi
if [ "$ecode" != "200" ]; then
  echo "❌ Ollama embeddings failed: http=$ecode body=$(head -c 2000 "$TMP_EMB" 2>/dev/null || true)" >&2
  exit 1
fi

# 3) Convert embedding -> qdrant query JSON (no pipes)
"$PY" - <<'PY' "$TMP_EMB" "$TMP_QRY"
import json, sys, os
src, dst = sys.argv[1], sys.argv[2]
with open(src, "r", encoding="utf-8") as f:
    j = json.load(f)
v = j.get("embedding")
if not isinstance(v, list) or not v:
    raise SystemExit("❌ empty embedding in response")
with open(dst, "w", encoding="utf-8") as f:
    json.dump({"vector": v, "limit": 3, "with_payload": True}, f)
print(f"WROTE_QRY bytes={os.path.getsize(dst)}", file=sys.stderr)
PY

# 4) Get dims (debug)
DIM="$("$PY" -c 'import json,sys; j=json.load(open(sys.argv[1],"r",encoding="utf-8")); v=j.get("embedding") or []; print(len(v) if isinstance(v,list) else "")' "$TMP_EMB")"

ccode="$(curl -sS -m 10 -o "$TMP_COLL" -w '%{http_code}' \
  "$QDRANT/collections/$COLL" || true)"

CSZ=""
if [ "$ccode" = "200" ]; then
  CSZ="$("$PY" -c 'import json,sys; j=json.load(open(sys.argv[1],"r",encoding="utf-8")); print(j["result"]["config"]["params"]["vectors"]["size"])' "$TMP_COLL")"
fi

echo "== dims =="
echo "embed_dim=${DIM:-?} collection_size=${CSZ:-?} (coll_http=$ccode)"

# 5) Qdrant search (first try)
qcode="$(curl -sS -m 60 -o "$TMP_QRES" -w '%{http_code}' \
  "$QDRANT/collections/$COLL/points/search" \
  -H 'Content-Type: application/json' \
  --data-binary @"$TMP_QRY" || true)"

# If 400 due to named vectors requirement, retry with {"vector":{"name":"default","vector":[...]}}
if [ "$qcode" = "400" ] && rg -q "named vectors|Named vectors|vector name" "$TMP_QRES" 2>/dev/null; then
  "$PY" - <<'PY' "$TMP_QRY"
import json,sys
p=sys.argv[1]
j=json.load(open(p,"r",encoding="utf-8"))
v=j.get("vector")
j["vector"]={"name":"default","vector":v}
json.dump(j, open(p,"w",encoding="utf-8"))
print("REWROTE_QRY_named_vectors", file=sys.stderr)
PY

  qcode="$(curl -sS -m 60 -o "$TMP_QRES" -w '%{http_code}' \
    "$QDRANT/collections/$COLL/points/search" \
    -H 'Content-Type: application/json' \
    --data-binary @"$TMP_QRY" || true)"
fi

if [ "$qcode" = "000" ]; then
  echo "❌ Qdrant not reachable at $QDRANT" >&2
  exit 1
fi
if [ "$qcode" != "200" ]; then
  echo "❌ Qdrant search failed: http=$qcode body=$(head -c 2500 "$TMP_QRES" 2>/dev/null || true)" >&2
  echo "DEBUG: qry_head=$(head -c 220 "$TMP_QRY" 2>/dev/null || true)" >&2
  echo "HINT: if embed_dim != collection_size, re-run ./scripts/index_libs_qdrant.sh (it recreates on mismatch)." >&2
  exit 1
fi

echo "== qdrant top hits =="
"$PY" - <<'PY' <"$TMP_QRES"
import json,sys
j=json.load(sys.stdin)
hits=j.get("result",[])
print(f"hits={len(hits)}")
for i,h in enumerate(hits[:3],1):
    p=h.get("payload",{}) or {}
    score=h.get("score")
    try: score_s=f"{float(score):.4f}"
    except Exception: score_s=str(score)
    print(f"{i}. score={score_s} feature={p.get('feature')} lib_id={p.get('lib_id')}")
PY

echo "✅ SMOKE_RAG_OK"
