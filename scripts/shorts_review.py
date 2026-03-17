#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent


def latest_job_dir() -> Path | None:
    base = ROOT / "artifacts"
    if not base.exists():
        return None
    jobs = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("shorts_")]
    if not jobs:
        return None
    jobs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return jobs[0]


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _file_url(relpath: str) -> str:
    return "/files/" + relpath.replace("\\", "/")


def _artifact_map(artifacts):
    by_kind = {}
    for a in artifacts or []:
        kind = a.get("kind", "")
        path = a.get("path", "")
        by_kind.setdefault(kind, []).append(path)
    return by_kind


def _clip_index_from_path(path: str) -> int:
    m = re.search(r'(\d+)(?=\.[A-Za-z0-9]+$)', path)
    if not m:
        m = re.search(r'(\d+)', path)
    return int(m.group(1)) if m else 0


def _build_clips_from_manifest(manifest: dict) -> list[dict]:
    artifacts = manifest.get("artifacts", []) or []
    amap = _artifact_map(artifacts)

    meta_by_idx = {}
    for mp in amap.get("clip_metadata", []):
        obj = _read_json(ROOT / mp, {})
        meta_by_idx[_clip_index_from_path(mp)] = obj

    vids = {_clip_index_from_path(x): x for x in amap.get("short_video", [])}
    caps = {_clip_index_from_path(x): x for x in amap.get("short_video_captioned", [])}
    thumbs = {_clip_index_from_path(x): x for x in amap.get("thumbnail", [])}
    srts = {_clip_index_from_path(x): x for x in amap.get("subtitle", [])}
    vtts = {_clip_index_from_path(x): x for x in amap.get("subtitle_vtt", [])}

    all_idx = sorted(set(vids) | set(caps) | set(thumbs) | set(srts) | set(vtts) | set(meta_by_idx))
    clips = []

    for idx in all_idx:
        meta = meta_by_idx.get(idx, {})
        clips.append({
            "index": idx,
            "title": ((meta.get("title_variants") or [None])[0] or meta.get("title") or f"Clip {idx:02d}"),
            "hook": ((meta.get("hook_variants") or [None])[0] or meta.get("hook") or ""),
            "story_role": meta.get("story_role", ""),
            "backstory_context": meta.get("backstory_context", ""),
            "thumbnail_text": meta.get("thumbnail_text", ""),
            "thumbnail_variants": meta.get("thumbnail_variants", []),
            "title_variants": meta.get("title_variants", []),
            "hook_variants": meta.get("hook_variants", []),
            "video_path": vids.get(idx),
            "captioned_video_path": caps.get(idx),
            "thumbnail_path": thumbs.get(idx),
            "subtitle_path": srts.get(idx),
            "subtitle_vtt_path": vtts.get(idx),
            "video_url": _file_url(vids[idx]) if idx in vids else None,
            "captioned_video_url": _file_url(caps[idx]) if idx in caps else None,
            "thumbnail_url": _file_url(thumbs[idx]) if idx in thumbs else None,
            "subtitle_url": _file_url(srts[idx]) if idx in srts else None,
            "subtitle_vtt_url": _file_url(vtts[idx]) if idx in vtts else None,
        })

    return clips


def build_payload():
    latest = latest_job_dir()
    if not latest:
        return {"ok": False, "clips": []}

    manifest_path = latest / "brief" / "package_manifest.json"
    manifest = _read_json(manifest_path, {}) if manifest_path.exists() else {}

    zip_path = latest / "exports" / f"{latest.name}.zip"
    zip_rel = str(zip_path.relative_to(ROOT)) if zip_path.exists() else None

    return {
        "ok": True,
        "job_id": latest.name,
        "job_path": str(latest.relative_to(ROOT)),
        "zip": zip_rel,
        "manifest": manifest,
        "clips": _build_clips_from_manifest(manifest),
    }


HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Shorts Review UI</title>
  <style>
    :root { color-scheme: dark; }
    body { margin:0; font-family:Arial,Helvetica,sans-serif; background:#0b0d12; color:#f3f5f7; }
    .top { position:sticky; top:0; z-index:5; background:#11161f; padding:16px; border-bottom:1px solid #202838; }
    .row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
    .title { font-size:20px; font-weight:700; }
    .muted { color:#9aa4b2; }
    .controls input,.controls select,.controls button,a.btn {
      background:#151c27; color:#f3f5f7; border:1px solid #2a3446; border-radius:10px;
      padding:10px 12px; text-decoration:none;
    }
    .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(360px,1fr)); gap:16px; padding:16px; }
    .card { background:#121826; border:1px solid #202838; border-radius:18px; overflow:hidden; box-shadow:0 10px 30px rgba(0,0,0,.25); }
    .thumb { width:100%; aspect-ratio:9/16; object-fit:cover; background:#0d1117; display:block; }
    .body { padding:14px; }
    .k { font-size:12px; color:#9aa4b2; text-transform:uppercase; letter-spacing:.08em; }
    .h { font-size:18px; font-weight:700; margin:6px 0; }
    .p { font-size:14px; color:#c8d0da; line-height:1.4; }
    video { width:100%; background:black; display:block; }
    .actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }
    .pill { display:inline-block; padding:4px 8px; background:#192131; border:1px solid #293246; border-radius:999px; font-size:12px; margin-right:6px; margin-top:6px; }
    pre { white-space:pre-wrap; word-break:break-word; background:#0d1117; padding:10px; border-radius:12px; border:1px solid #202838; }
  </style>
</head>
<body>
  <div class="top">
    <div class="row">
      <div>
        <div class="title">Shorts Review UI</div>
        <div id="jobLine" class="muted">Loading…</div>
      </div>
      <div class="controls row" style="margin-left:auto">
        <input id="search" placeholder="Search title / hook / context" />
        <select id="sortBy">
          <option value="index">Sort: Clip order</option>
          <option value="title">Sort: Title</option>
          <option value="story_role">Sort: Story role</option>
        </select>
        <button id="refreshBtn">Refresh</button>
        <a id="zipBtn" class="btn" target="_blank" style="display:none">Download ZIP</a>
      </div>
    </div>
  </div>

  <div id="grid" class="grid"></div>

<script>
let DATA = null;
const grid = document.getElementById("grid");
const searchEl = document.getElementById("search");
const sortByEl = document.getElementById("sortBy");
const refreshBtn = document.getElementById("refreshBtn");
const zipBtn = document.getElementById("zipBtn");
const jobLine = document.getElementById("jobLine");

function fileHref(rel) { return "/files/" + rel.replaceAll("\\\\", "/"); }

function esc(s) {
  return String(s ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}

function card(c) {
  const thumb = c.thumbnail_url ? `<img class="thumb" src="${esc(c.thumbnail_url)}" loading="lazy">` : "";
  const playable = c.captioned_video_url || c.video_url || "";
  const video = playable ? `<video controls preload="metadata" src="${esc(playable)}"></video>` : "";
  const thumbVars = (c.thumbnail_variants || []).map(x => `<span class="pill">${esc(x)}</span>`).join("");
  const titleVars = (c.title_variants || []).map(x => `<span class="pill">${esc(x)}</span>`).join("");
  const hookVars = (c.hook_variants || []).map(x => `<span class="pill">${esc(x)}</span>`).join("");

  return `
    <div class="card">
      ${thumb}
      ${video}
      <div class="body">
        <div class="k">Clip ${String(c.index).padStart(2, "0")} ${c.story_role ? "• " + esc(c.story_role) : ""}</div>
        <div class="h">${esc(c.title || "")}</div>
        <div class="p">${esc(c.hook || "")}</div>
        ${c.backstory_context ? `<pre>${esc(c.backstory_context)}</pre>` : ""}
        ${thumbVars ? `<div><div class="k">Thumbnail variants</div>${thumbVars}</div>` : ""}
        ${titleVars ? `<div><div class="k">Title variants</div>${titleVars}</div>` : ""}
        ${hookVars ? `<div><div class="k">Hook variants</div>${hookVars}</div>` : ""}
        <div class="actions">
          ${c.captioned_video_url ? `<a class="btn" href="${esc(c.captioned_video_url)}" target="_blank">Captioned MP4</a>` : ""}
          ${c.video_url ? `<a class="btn" href="${esc(c.video_url)}" target="_blank">Original MP4</a>` : ""}
          ${c.subtitle_url ? `<a class="btn" href="${esc(c.subtitle_url)}" target="_blank">SRT</a>` : ""}
          ${c.subtitle_vtt_url ? `<a class="btn" href="${esc(c.subtitle_vtt_url)}" target="_blank">VTT</a>` : ""}
          ${c.thumbnail_url ? `<a class="btn" href="${esc(c.thumbnail_url)}" target="_blank">Thumbnail</a>` : ""}
        </div>
      </div>
    </div>
  `;
}

function render() {
  if (!DATA) return;
  let clips = [...(DATA.clips || [])];
  const q = searchEl.value.trim().toLowerCase();

  if (q) {
    clips = clips.filter(c => {
      const text = [
        c.title, c.hook, c.story_role, c.backstory_context,
        ...(c.title_variants || []), ...(c.hook_variants || []), ...(c.thumbnail_variants || [])
      ].join(" ").toLowerCase();
      return text.includes(q);
    });
  }

  const sortBy = sortByEl.value;
  clips.sort((a, b) => {
    if (sortBy === "title") return String(a.title || "").localeCompare(String(b.title || ""));
    if (sortBy === "story_role") return String(a.story_role || "").localeCompare(String(b.story_role || ""));
    return (a.index || 0) - (b.index || 0);
  });

  grid.innerHTML = clips.map(card).join("");
}

async function loadData() {
  const res = await fetch("/api/latest", { cache: "no-store" });
  DATA = await res.json();

  if (DATA && DATA.ok) {
    jobLine.textContent = `${DATA.job_id} • ${DATA.clips?.length || 0} clips`;
    if (DATA.zip) {
      zipBtn.style.display = "";
      zipBtn.href = fileHref(DATA.zip);
    } else {
      zipBtn.style.display = "none";
    }
  } else {
    jobLine.textContent = "No shorts job found";
    zipBtn.style.display = "none";
  }

  render();
}

sortByEl.addEventListener("change", render);
searchEl.addEventListener("input", render);
refreshBtn.addEventListener("click", loadData);
loadData();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, status=200, content_type="text/plain; charset=utf-8", body=b""):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def _send_file(self, fpath, content_type="application/octet-stream"):
        size = fpath.stat().st_size
        range_header = self.headers.get("Range", "").strip()

        start = 0
        end = size - 1
        status = 200

        if range_header.startswith("bytes="):
            spec = range_header.split("=", 1)[1].strip()
            if "," not in spec:
                left, _, right = spec.partition("-")
                try:
                    if left and right:
                        start = int(left)
                        end = int(right)
                    elif left:
                        start = int(left)
                        end = size - 1
                    elif right:
                        suffix = int(right)
                        start = max(0, size - suffix)
                        end = size - 1

                    if start < 0:
                        start = 0
                    if end >= size:
                        end = size - 1

                    if start > end or start >= size:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{size}")
                        self.send_header("Accept-Ranges", "bytes")
                        self.end_headers()
                        return

                    status = 206
                except Exception:
                    start = 0
                    end = size - 1
                    status = 200

        length = end - start + 1

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()

        try:
            with open(fpath, "rb") as fh:
                fh.seek(start)
                remaining = length
                chunk_size = 256 * 1024
                while remaining > 0:
                    chunk = fh.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._send(200, "text/html; charset=utf-8", HTML.encode("utf-8"))
            return

        if path == "/api/latest":
            payload = json.dumps(build_payload(), indent=2).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", payload)
            return

        if path.startswith("/files/"):
            relpath = unquote(path[len("/files/"):]).lstrip("/")
            fpath = (ROOT / relpath).resolve()

            try:
                fpath.relative_to(ROOT.resolve())
            except Exception:
                self._send(403, body=b"forbidden")
                return

            if not fpath.exists() or not fpath.is_file():
                self._send(404, body=b"not found")
                return

            ctype, _ = mimetypes.guess_type(str(fpath))
            if not ctype:
                ctype = "application/octet-stream"
            self._send_file(fpath, ctype)
            return

        self._send(404, body=b"not found")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8788"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Shorts review UI: http://127.0.0.1:{port}")
    server.serve_forever()
