def score_text(text):
    t = text.lower()
    score = 0
    if any(x in t for x in ["wait", "what", "no way", "imagine", "secret"]):
        score += 30
    if len(text) > 80:
        score += 20
    if "!" in text:
        score += 10
    return score

def build_candidates(transcript, scenes):
    clips = []

    for i, sc in enumerate(scenes):
        segs = [t for t in transcript if t["start"] >= sc["start"] and t["end"] <= sc["end"]]
        if not segs:
            continue

        text = " ".join([s["text"] for s in segs])
        score = score_text(text)

        clips.append({
            "name": f"clip_{i}",
            "start": sc["start"],
            "end": sc["end"],
            "text": text,
            "score": score,
            "status": "candidate"
        })

    clips.sort(key=lambda x: x["score"], reverse=True)
    return clips[:15]
