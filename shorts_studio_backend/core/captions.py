from __future__ import annotations

def build_caption_segments(transcript: list[dict], start: float, end: float) -> list[dict]:
    out = []
    for seg in transcript:
        s = float(seg.get("start", 0))
        e = float(seg.get("end", 0))
        if e < start or s > end:
            continue
        out.append({
            "start": max(0.0, s - start),
            "end": max(0.0, e - start),
            "text": seg.get("text", "").strip(),
        })
    return out

def hook_words(text: str) -> list[str]:
    hits = []
    for w in ["wait", "what", "no way", "secret", "imagine", "crazy", "why", "how"]:
        if w in text.lower():
            hits.append(w)
    return hits
