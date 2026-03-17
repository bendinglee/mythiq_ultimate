from scenedetect import open_video, SceneManager
from scenedetect.detectors import ContentDetector

def detect_scenes(video_path):
    video = open_video(video_path, backend="pyav")
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=27.0))
    sm.detect_scenes(video)

    scenes = []
    for s in sm.get_scene_list():
        scenes.append({
            "start": s[0].get_seconds(),
            "end": s[1].get_seconds()
        })
    return scenes
