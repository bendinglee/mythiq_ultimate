#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:7777}"

curl -fsS "$BASE/v1/artifacts/latest?feature=image" >/dev/null

echo "SMOKE_ARTIFACT_LATEST_OK"
