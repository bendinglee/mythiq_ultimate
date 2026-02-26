#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/.venv/bin/python"

"$PY" - <<'PY'
from api.app.db import init_db, connect
init_db()
conn = connect()
try:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='pattern_variants'"
    ).fetchone()
    assert row and row[0] == "pattern_variants", "missing table: pattern_variants"
finally:
    conn.close()
print("SMOKE_DB_OK")
PY
