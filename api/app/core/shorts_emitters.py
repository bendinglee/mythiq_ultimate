from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import hashlib
import re


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s[:48] or "shortsgen"


def emit_shorts_bundle(topic: str, content: str) -> Dict[str, Any]:
    key = hashlib.sha1(topic.encode("utf-8")).hexdigest()[:12]
    root = Path("projects") / f"shorts_{key}" / "shortsgen" / _slug(topic)
    root.mkdir(parents=True, exist_ok=True)

    blueprint_md = root / "BLUEPRINT.md"
    hooks_md = root / "HOOKS.md"
    edit_json = root / "edit_plan.json"

    blueprint_md.write_text(content, encoding="utf-8")

    hooks = []
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("1. ") or s.startswith("2. ") or s.startswith("3. "):
            hooks.append(s[3:])

    hooks_md.write_text(
        "# Hook Variants\n\n" + "\n".join(f"- {h}" for h in hooks) + "\n",
        encoding="utf-8",
    )

    edit_json.write_text(
        """{
  "timeline": [
    {"range": "0-2s", "beat": "Hook"},
    {"range": "2-6s", "beat": "Context"},
    {"range": "6-12s", "beat": "Escalation"},
    {"range": "12-18s", "beat": "Payoff"},
    {"range": "18-22s", "beat": "Loop / CTA"}
  ],
  "style": {
    "captions": "subtitle-first",
    "pacing": "hard visual change every 1-2 seconds",
    "ending": "loop back to the opening line"
  }
}
""",
        encoding="utf-8",
    )

    files: List[str] = [str(blueprint_md), str(hooks_md), str(edit_json)]
    return {
        "root": str(root),
        "files": files,
        "file_count": len(files),
    }
