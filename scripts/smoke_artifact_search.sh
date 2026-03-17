#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:7777}"

curl -fsS "$BASE/v1/artifacts/search?limit=5" >/dev/null
curl -fsS "$BASE/v1/artifacts/search?feature=image&limit=5" >/dev/null

echo "SMOKE_ARTIFACT_SEARCH_OK"
