from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from shorts_studio_backend.core.transcribe import transcribe
from shorts_studio_backend.core.scenes import detect_scenes
from shorts_studio_backend.core.candidates import build_candidates
from shorts_studio_backend.core.render import render_preview
from shorts_studio_backend.core.storage_gc import dir_size_bytes, cleanup_trash
from shorts_studio_backend.core.final_render import render_final, write_ass
from shorts_studio_backend.core.captions import build_caption_segments, hook_words

ROOT = Path.home() / "mythiq_ultimate"
STORAGE = ROOT / "shorts_studio" / "storage"
UPLOADS = STORAGE / "uploads"
PREVIEWS = STORAGE / "previews"
EXPORTS = STORAGE / "exports"
TRASH = STORAGE / "trash"
MANIFESTS = STORAGE / "manifests"
FINAL = STORAGE / "final"

for d in [UPLOADS, PREVIEWS, EXPORTS, TRASH, MANIFESTS, FINAL]:
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Shorts Studio Backend")

class DecisionReq(BaseModel):
    project_id: str
    clip_name: str

class FinalRenderReq(BaseModel):
    project_id: str
    clip_name: str
    mode: str = "tiktok_4k"
    burn_captions: bool = True

def manifest_path(pid: str) -> Path:
    return MANIFESTS / f"{pid}.json"

def save_manifest(pid: str, data: dict[str, Any]) -> None:
    manifest_path(pid).write_text(json.dumps(data, indent=2), encoding="utf-8")

def load_manifest(pid: str) -> dict[str, Any]:
    p = manifest_path(pid)
    if not p.exists():
        raise HTTPException(status_code=404, detail="project not found")
    return json.loads(p.read_text(encoding="utf-8"))

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/upload")
async def upload(file: UploadFile):
    pid = str(uuid.uuid4())[:8]
    filename = file.filename or "upload.mp4"
    path = UPLOADS / f"{pid}_{filename}"

    with open(path, "wb") as f:
        f.write(await file.read())

    data = {
        "project_id": pid,
        "video": str(path),
        "clips": [],
        "kept": [],
        "discarded": [],
    }
    save_manifest(pid, data)
    return data

@app.post("/analyze")
def analyze(req: dict[str, Any]):
    pid = req["project_id"]
    data = load_manifest(pid)

    video = data["video"]
    transcript = transcribe(video)
    scenes = detect_scenes(video)
    clips = build_candidates(transcript, scenes)

    preview_dir = PREVIEWS / pid
    for c in clips:
        c["path"] = render_preview(video, c, preview_dir)

    data["clips"] = clips
    save_manifest(pid, data)
    return data

@app.get("/project/{pid}")
def get_project(pid: str):
    return load_manifest(pid)

@app.post("/keep")
def keep_clip(req: DecisionReq) -> dict[str, Any]:
    data = load_manifest(req.project_id)
    found = next((c for c in data["clips"] if c["name"] == req.clip_name), None)
    if not found:
        raise HTTPException(status_code=404, detail="clip not found")

    found["status"] = "kept"
    if req.clip_name not in data["kept"]:
        data["kept"].append(req.clip_name)
    if req.clip_name in data["discarded"]:
        data["discarded"].remove(req.clip_name)

    save_manifest(req.project_id, data)
    return data

@app.post("/discard")
def discard_clip(req: DecisionReq) -> dict[str, Any]:
    data = load_manifest(req.project_id)
    found = next((c for c in data["clips"] if c["name"] == req.clip_name), None)
    if not found:
        raise HTTPException(status_code=404, detail="clip not found")

    src = Path(found["path"])
    trash_dir = TRASH / req.project_id
    trash_dir.mkdir(parents=True, exist_ok=True)

    if src.exists():
        shutil.move(str(src), str(trash_dir / src.name))

    found["status"] = "discarded"
    if req.clip_name not in data["discarded"]:
        data["discarded"].append(req.clip_name)
    if req.clip_name in data["kept"]:
        data["kept"].remove(req.clip_name)

    save_manifest(req.project_id, data)
    return data

@app.post("/export/{project_id}")
def export_project(project_id: str) -> dict[str, Any]:
    data = load_manifest(project_id)
    kept = [c for c in data["clips"] if c.get("status") == "kept"]
    if not kept:
        raise HTTPException(status_code=400, detail="no kept clips")

    out_dir = EXPORTS / project_id
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "README.txt").write_text(
        "Shorts Studio export bundle\nOnly kept clips are included.\n",
        encoding="utf-8",
    )
    (out_dir / "manifest.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    for clip in kept:
        src = Path(clip["path"])
        if src.exists():
            shutil.copy2(src, out_dir / src.name)

    zip_base = EXPORTS / f"{project_id}_bundle"
    zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=out_dir)
    return {"ok": True, "zip": zip_path}

@app.get("/download")
def download(path: str) -> FileResponse:
    p = Path(path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="file missing")
    return FileResponse(p)


@app.get("/storage/stats")
def storage_stats():
    roots = {
        "uploads": str(UPLOADS),
        "previews": str(PREVIEWS),
        "exports": str(EXPORTS),
        "trash": str(TRASH),
    }
    return {
        "ok": True,
        "bytes": {k: dir_size_bytes(v) for k, v in roots.items()}
    }

@app.post("/storage/cleanup")
def storage_cleanup():
    removed = cleanup_trash(str(TRASH), ttl_hours=24)
    return {"ok": True, "removed": removed, "count": len(removed)}


@app.post("/final-render")
def final_render_endpoint(req: FinalRenderReq):
    data = load_manifest(req.project_id)
    clip = next((c for c in data["clips"] if c["name"] == req.clip_name), None)
    if not clip:
        raise HTTPException(status_code=404, detail="clip not found")

    src = data["video"]
    out_dir = FINAL / req.project_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{req.clip_name}_{req.mode}.mp4"

    ass_path = None
    if req.burn_captions:
        transcript = transcribe(src)
        subs = build_caption_segments(transcript, clip["start"], clip["end"])
        ass_path = str(out_dir / f"{req.clip_name}.ass")
        write_ass(subs, ass_path)

    try:
        rendered = render_final(
        src=src,
        start=float(clip["start"]),
        end=float(clip["end"]),
        out_path=str(out_path),
        mode=req.mode,
        ass_path=ass_path,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "final_render_failed",
                "message": str(e),
                "burn_captions": bool(getattr(req, "burn_captions", False)),
                "ass_path": ass_path if "ass_path" in locals() else None,
                "final_path": str(final_path) if "final_path" in locals() else None,
            },
        )

    clip["final_path"] = rendered
    clip["hook_words"] = hook_words(clip.get("text", ""))
    save_manifest(req.project_id, data)

    return {
    "ok": True,
    "project_id": req.project_id,
    "clip_name": req.clip_name,
    "final_path": rendered["final_path"],
    "ass_path": ass_path,
    "hook_words": hook_words,
    "burn_captions_requested": rendered["burn_captions_requested"],
    "burn_captions_applied": rendered["burn_captions_applied"],
    "warning": rendered["warning"],
}
