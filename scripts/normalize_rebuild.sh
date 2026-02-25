#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'PY'
from pathlib import Path
import re

p = Path("scripts/rebuild.sh")
s = p.read_text(encoding="utf-8", errors="ignore")

# 1) remove any existing guard block (we will re-add one canonical block)
s = re.sub(r'(?s)\n# --- fail-fast guards ---\n.*?# --- end guards ---\n\n', "\n", s)

# 2) ensure the cd line exists
if 'cd "$(dirname "$0")/.."' not in s:
    raise SystemExit('❌ expected: cd "$(dirname "$0")/.." in scripts/rebuild.sh')

# 3) insert canonical guard block right after cd line
guard = (
    '\n# --- fail-fast guards ---\n'
    './scripts/verify_api.sh >/dev/null\n'
    'python3 scripts/fix_route_indent.py api/app/main.py /v1/ab_pick >/dev/null\n'
    'python3 -m py_compile api/app/main.py\n'
    '# --- end guards ---\n\n'
)

s = re.sub(r'(?m)^(cd\s+"\$\(\s*dirname\s+"\$0"\s*\)/\.\."\s*\n)',
           r'\1' + guard,
           s,
           count=1)

# 4) ensure test_ab runs after wait_ready (remove elsewhere, then insert after first wait_ready line)
s = re.sub(r'(?m)^\./scripts/test_ab\.sh\s*>/dev/null\s*\n', '', s)
s = re.sub(r'(?m)^(\./scripts/wait_ready\.sh[^\n]*\n)', r'\1./scripts/test_ab.sh >/dev/null\n', s, count=1)

p.write_text(s, encoding="utf-8")
print("✅ normalized scripts/rebuild.sh")
PY
