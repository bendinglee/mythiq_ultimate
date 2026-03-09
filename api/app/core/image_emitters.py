from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import hashlib
import json
import re


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s[:48] or "imagegen"


def emit_image_bundle(prompt: str, content: str) -> Dict[str, Any]:
    key = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12]
    root = Path("projects") / f"image_{key}" / "imagegen" / _slug(prompt)
    root.mkdir(parents=True, exist_ok=True)

    prompt_json = root / "prompt.json"
    storyboard_json = root / "storyboard.json"
    render_plan_json = root / "render_plan.json"

    prompt_json.write_text(
        json.dumps({"prompt": prompt, "content": content}, indent=2),
        encoding="utf-8",
    )

    storyboard_json.write_text(
        json.dumps(
            {
                "frames": [
                    {"frame": 1, "description": prompt},
                    {"frame": 2, "description": "close-up detail"},
                    {"frame": 3, "description": "cinematic wide angle"},
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    render_plan_json.write_text(
        json.dumps(
            {
                "resolution": "1024x1024",
                "style": "illustration",
                "lighting": "cinematic",
                "camera": "dynamic framing",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    files: List[str] = [
        str(prompt_json),
        str(storyboard_json),
        str(render_plan_json),
    ]

    return {
        "root": str(root),
        "files": files,
        "file_count": len(files),
    }
