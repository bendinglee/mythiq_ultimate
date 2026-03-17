#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path


def ffprobe_json(path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        path,
    ]
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out)


def get_video_stream(meta: dict) -> dict:
    for s in meta.get("streams", []):
        if s.get("codec_type") == "video":
            return s
    raise RuntimeError("no video stream found")


def get_audio_stream(meta: dict) -> dict | None:
    for s in meta.get("streams", []):
        if s.get("codec_type") == "audio":
            return s
    return None


def clamp(x: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, x))


def score_from_meta(path: str) -> dict:
    meta = ffprobe_json(path)
    video = get_video_stream(meta)
    audio = get_audio_stream(meta)
    fmt = meta.get("format", {})

    width = int(video.get("width", 0) or 0)
    height = int(video.get("height", 0) or 0)
    duration = float(fmt.get("duration", 0) or 0.0)
    size = int(fmt.get("size", 0) or 0)

    bitrate = 0
    try:
        bitrate = int(fmt.get("bit_rate", 0) or 0)
    except Exception:
        bitrate = 0

    # Heuristic scores only. This is a machine gate, not human truth.
    visual_finish = 8.5 if (width == 2160 and height == 3840) else 6.5 if (width == 1080 and height == 1920) else 4.0
    compression = 8.0 if bitrate >= 8_000_000 else 6.5 if bitrate >= 3_000_000 else 4.5
    duration_score = 8.5 if 12 <= duration <= 35 else 7.0 if 8 <= duration <= 45 else 4.5
    file_score = 8.0 if size >= 1_000_000 else 5.0
    audio_score = 7.5 if audio else 3.0

    # Placeholder editorial scores until deeper evaluator exists
    hook = 7.0
    story = 7.0
    pacing = clamp((duration_score + compression) / 2)
    payoff = 7.0
    captions = 7.0
    transitions = 7.0
    replay_value = 6.8
    platform_fit = 8.5 if height > width else 3.0

    overall = round(sum([
        hook, story, pacing, payoff, captions,
        transitions, audio_score, visual_finish,
        replay_value, platform_fit
    ]) / 10.0, 2)

    return {
        "path": str(Path(path).resolve()),
        "width": width,
        "height": height,
        "duration": round(duration, 3),
        "bitrate": bitrate,
        "size_bytes": size,
        "hook": round(hook, 2),
        "story": round(story, 2),
        "pacing": round(pacing, 2),
        "payoff": round(payoff, 2),
        "captions": round(captions, 2),
        "transitions": round(transitions, 2),
        "audio": round(audio_score, 2),
        "visual_finish": round(visual_finish, 2),
        "replay_value": round(replay_value, 2),
        "platform_fit": round(platform_fit, 2),
        "overall": overall,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: short_quality_score.py /path/to/video.mp4", file=sys.stderr)
        return 2
    result = score_from_meta(sys.argv[1])
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
