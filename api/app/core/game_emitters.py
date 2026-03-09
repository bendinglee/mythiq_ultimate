from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import hashlib
import json
import re


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return s[:48] or "gamegen"


def emit_game_bundle(prompt: str, content: str) -> Dict[str, Any]:
    key = hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12]
    root = Path("projects") / f"game_{key}" / "gamegen" / _slug(prompt)
    root.mkdir(parents=True, exist_ok=True)

    index_html = root / "index.html"
    main_js = root / "main.js"
    game_config_json = root / "game_config.json"
    readme_md = root / "README.md"

    index_html.write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Mythiq Game Bundle</title>
  <style>
    body { margin: 0; font-family: system-ui, sans-serif; background: #0b1020; color: #fff; }
    .wrap { max-width: 960px; margin: 0 auto; padding: 24px; }
    canvas { display: block; width: 100%; max-width: 960px; height: auto; background: #111827; border: 1px solid #334155; }
    .meta { opacity: 0.85; margin-top: 12px; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Mythiq Game Bundle</h1>
    <canvas id="game" width="960" height="540"></canvas>
    <div class="meta">Open <code>main.js</code> to extend the prototype.</div>
  </div>
  <script src="./main.js"></script>
</body>
</html>
""",
        encoding="utf-8",
    )

    main_js.write_text(
        """const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

let t = 0;
let x = 120;
let dir = 1;

function draw() {
  t += 1;
  x += dir * 2;
  if (x > 840) dir = -1;
  if (x < 120) dir = 1;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "#0f172a";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "#1e293b";
  ctx.fillRect(0, 420, canvas.width, 120);

  ctx.fillStyle = "#22c55e";
  ctx.fillRect(x, 360, 64, 64);

  ctx.fillStyle = "#e2e8f0";
  ctx.font = "24px system-ui, sans-serif";
  ctx.fillText("Mythiq prototype loop", 24, 40);

  ctx.font = "18px system-ui, sans-serif";
  ctx.fillText("Expand this scaffold into a real playable build.", 24, 72);

  requestAnimationFrame(draw);
}

draw();
""",
        encoding="utf-8",
    )

    game_config_json.write_text(
        json.dumps(
            {
                "title": "Mythiq Game Bundle",
                "prompt": prompt,
                "engine": "html5_canvas",
                "resolution": {"width": 960, "height": 540},
                "loop": [
                    "player action",
                    "system response",
                    "reward/progression",
                    "repeat with increasing mastery",
                ],
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    readme_md.write_text(
        f"""# Mythiq Game Bundle

## Prompt
{prompt}

## Files
- `index.html` - playable browser entry
- `main.js` - lightweight prototype loop
- `game_config.json` - design + runtime config
- `README.md` - bundle notes

## Design Blueprint
{content}
""",
        encoding="utf-8",
    )

    files: List[str] = [
        str(index_html),
        str(main_js),
        str(game_config_json),
        str(readme_md),
    ]

    return {
        "root": str(root),
        "files": files,
        "file_count": len(files),
    }
