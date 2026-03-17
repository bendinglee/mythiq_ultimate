#!/usr/bin/env python3
from __future__ import annotations

import json
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
OUT_DIR = ROOT / "web" / "shorts_review"


def latest_job() -> Path:
    jobs = [p for p in ARTIFACTS.glob("shorts_*") if p.is_dir()]
    if not jobs:
        raise SystemExit("No shorts_* artifact folders found")
    return max(jobs, key=lambda p: p.stat().st_mtime)


def rel(p: Path) -> str:
    return "/" + str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def normalize_tags(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        out = []
        for x in value:
            s = str(x).strip()
            if not s:
                continue
            if not s.startswith("#"):
                s = "#" + s.replace(" ", "")
            out.append(s)
        return out
    s = str(value).strip()
    if not s:
        return []
    if "," in s:
        return normalize_tags([x.strip() for x in s.split(",") if x.strip()])
    return [s if s.startswith("#") else "#" + s.replace(" ", "")]


def fallback_title(idx: int) -> str:
    return f"Mythiq Short {idx:02d}"


def fallback_desc(idx: int) -> str:
    return f"Auto-generated short #{idx:02d} reviewed locally in Mythiq."


def pick_video(renders_dir: Path, idx: int) -> Path | None:
    preferred = renders_dir / f"short_{idx:02d}.captioned.mp4"
    plain = renders_dir / f"short_{idx:02d}.mp4"
    if preferred.exists():
        return preferred
    if plain.exists():
        return plain

    # fallback by pattern
    matches = sorted(renders_dir.glob(f"short_{idx:02d}*.mp4"))
    return matches[0] if matches else None


def collect_items(job: Path) -> list[dict]:
    clips_dir = job / "clips_meta"
    renders_dir = job / "renders"
    package_json = read_json(job / "brief" / "shorts_package.json") or {}
    package_items = package_json.get("shorts") if isinstance(package_json, dict) else None
    if not isinstance(package_items, list):
        package_items = []

    clip_jsons = sorted(clips_dir.glob("clip_*.json"))
    items: list[dict] = []

    # build lookup from package JSON by 1-based index if present
    pkg_lookup = {}
    for i, row in enumerate(package_items, 1):
        if isinstance(row, dict):
            pkg_lookup[i] = row

    for meta_path in clip_jsons:
        m = re.search(r"clip_(\d+)\.json$", meta_path.name)
        if not m:
            continue
        idx = int(m.group(1))
        meta = read_json(meta_path) or {}
        pkg = pkg_lookup.get(idx, {})

        video = pick_video(renders_dir, idx)
        if not video or not video.exists():
            continue

        title = (
            meta.get("title")
            or pkg.get("title")
            or fallback_title(idx)
        )

        description = (
            meta.get("description")
            or pkg.get("description")
            or fallback_desc(idx)
        )

        hashtags = normalize_tags(
            meta.get("hashtags")
            or pkg.get("hashtags")
            or pkg.get("tags")
            or meta.get("tags")
        )

        items.append({
            "index": idx,
            "title": str(title).strip(),
            "description": str(description).strip(),
            "hashtags": hashtags,
            "video_url": rel(video),
            "video_path": str(video),
            "meta_path": str(meta_path),
        })

    # fallback if clips_meta exists but produced nothing: infer from renders directly
    if not items and renders_dir.exists():
        vids = sorted(renders_dir.glob("short_*.mp4"))
        seen = set()
        for v in vids:
            m = re.search(r"short_(\d+)", v.name)
            if not m:
                continue
            idx = int(m.group(1))
            if idx in seen:
                continue
            best = pick_video(renders_dir, idx)
            if not best:
                continue
            seen.add(idx)
            items.append({
                "index": idx,
                "title": fallback_title(idx),
                "description": fallback_desc(idx),
                "hashtags": ["#shorts", "#mythiq"],
                "video_url": rel(best),
                "video_path": str(best),
                "meta_path": "",
            })

    items.sort(key=lambda x: x["index"])
    return items


def build_html(items: list[dict], json_url: str) -> str:
    cards = []
    for row in items:
        tags = " ".join(html.escape(x) for x in row.get("hashtags", []))
        cards.append(f"""
        <article class="card">
          <div class="meta">
            <h2>{html.escape(row["title"])}</h2>
            <p class="desc">{html.escape(row["description"])}</p>
            <p class="tags">{tags}</p>
          </div>
          <video controls playsinline preload="metadata" src="{html.escape(row["video_url"])}"></video>
        </article>
        """)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Mythiq Shorts Review</title>
<style>
:root {{
  color-scheme: dark;
}}
* {{
  box-sizing: border-box;
}}
body {{
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, Inter, sans-serif;
  background: #050b14;
  color: #eef2ff;
}}
header {{
  padding: 24px 20px 16px;
  border-bottom: 1px solid #1d2a44;
}}
h1 {{
  margin: 0 0 8px;
  font-size: 24px;
}}
.sub {{
  margin: 0;
  color: #a8b3cf;
}}
.wrap {{
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}}
.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 18px;
}}
.card {{
  background: #0c1526;
  border: 1px solid #1b2944;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,.25);
}}
.meta {{
  padding: 14px;
}}
.meta h2 {{
  margin: 0 0 8px;
  font-size: 18px;
  line-height: 1.25;
}}
.desc {{
  margin: 0 0 10px;
  color: #b8c4de;
  font-size: 14px;
  line-height: 1.45;
  white-space: pre-wrap;
}}
.tags {{
  margin: 0;
  color: #7dd3fc;
  font-size: 13px;
}}
video {{
  display: block;
  width: 100%;
  aspect-ratio: 9 / 16;
  background: #000;
}}
.toolbar {{
  display: flex;
  gap: 10px;
  align-items: center;
  margin: 0 0 18px;
  flex-wrap: wrap;
}}
input[type="search"] {{
  width: min(420px, 100%);
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid #253555;
  background: #08101d;
  color: #eef2ff;
}}
.small {{
  color: #94a3b8;
  font-size: 13px;
}}
</style>
</head>
<body>
<header>
  <h1>Mythiq Shorts Review</h1>
  <p class="sub">Local review page using existing rendered videos only. No duplicate video storage.</p>
</header>
<div class="wrap">
  <div class="toolbar">
    <input id="q" type="search" placeholder="Search title, description, hashtags" />
    <span class="small" id="count">{len(items)} shorts</span>
    <span class="small">{json_url}</span>
  </div>
  <div class="grid" id="grid">
    {''.join(cards)}
  </div>
</div>
<script>
const q = document.getElementById("q");
const grid = document.getElementById("grid");
const all = [...grid.querySelectorAll(".card")];
const count = document.getElementById("count");

q.addEventListener("input", () => {{
  const needle = q.value.toLowerCase().trim();
  let shown = 0;
  for (const card of all) {{
    const txt = card.innerText.toLowerCase();
    const ok = !needle || txt.includes(needle);
    card.style.display = ok ? "" : "none";
    if (ok) shown++;
  }}
  count.textContent = shown + " shorts";
}});
</script>
</body>
</html>
"""


def main() -> int:
    job = latest_job()
    items = collect_items(job)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "shorts_index.json"
    html_path = OUT_DIR / "index.html"

    json_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
    html_doc = build_html(items, "/web/shorts_review/shorts_index.json")
    html_path.write_text(html_doc, encoding="utf-8")

    print("REVIEW_PAGE_OK")
    print("JOB:", job)
    print("ITEMS:", len(items))
    print("INDEX:", html_path)
    print("JSON:", json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
