#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"

test -x "$PY" || { echo "❌ missing venv python: $PY"; exit 1; }

"$PY" - <<'PY'
import json
from pathlib import Path
from api.app.core.manifest_checks import validate_manifest

fixtures = sorted(Path("projects/_fixtures").glob("*/bundle/manifest.json"))
assert fixtures, "no fixture manifests found under projects/_fixtures"

for fp in fixtures:
    manifest = json.loads(fp.read_text(encoding="utf-8"))
    chk = validate_manifest(manifest)
    assert chk["ok"] is True, {"file": str(fp), "failures": chk["failures"]}

print("SMOKE_MANIFEST_REGRESSION_OK", len(fixtures))
PY
