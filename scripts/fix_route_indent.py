from __future__ import annotations
from pathlib import Path
import re
import sys

path = Path(sys.argv[1] if len(sys.argv) > 1 else "api/app/main.py")
route = sys.argv[2] if len(sys.argv) > 2 else "/v1/ab_pick"

s = path.read_text(encoding="utf-8", errors="ignore")
if route not in s:
    raise SystemExit(f"❌ route not found: {route}")

lines = s.splitlines(True)

# We look for:
#   <indent>apply_ab_to_library(conn, inp.ab_group)
#   decided = True        <-- specifically at column 0 (or less-indented than apply line)
#
# If found, re-indent decided=True to match apply line.
fixed = False
already_ok = False

for i in range(len(lines) - 1):
    if not re.search(r'^\s*apply_ab_to_library\s*\(\s*conn\s*,\s*inp\.ab_group\s*\)\s*$', lines[i]):
        continue

    apply_indent = re.match(r'^(\s*)', lines[i]).group(1)
    nxt = lines[i + 1]

    if not re.match(r'^\s*decided\s*=\s*True\s*$', nxt):
        continue

    nxt_indent = re.match(r'^(\s*)', nxt).group(1)

    if nxt_indent == apply_indent:
        already_ok = True
        break

    # Fix only if it's LESS indented than apply_indent (classic SyntaxError case)
    if len(nxt_indent) < len(apply_indent):
        lines[i + 1] = apply_indent + "decided = True\n"
        fixed = True
        break

if fixed:
    path.write_text("".join(lines), encoding="utf-8")
    print(f"✅ fixed indentation near {route}")
    raise SystemExit(0)

if already_ok:
    print(f"✅ indentation already OK near {route}")
    raise SystemExit(0)

print(f"ℹ️ no apply_ab_to_library()+decided=True pair found near {route} (nothing to do)")
