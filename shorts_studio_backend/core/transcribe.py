from faster_whisper import WhisperModel

_model = None

def get_model():
    global _model
    if _model is None:
        _model = WhisperModel("base", compute_type="int8")
    return _model

def transcribe(video_path):
    model = get_model()
    segments, _ = model.transcribe(video_path)

    out = []
    for s in segments:
        out.append({
            "start": float(s.start),
            "end": float(s.end),
            "text": s.text.strip()
        })
    return out
