import json
import os
from pathlib import Path

root = Path(".").resolve()
run_id = os.environ["RUN_ID"]

project = root / "shortforge" / "projects" / run_id
project.mkdir(parents=True, exist_ok=True)

scene_json = project / "analysis" / "scenes.json"
out_json = project / "analysis" / "scene_candidates.json"

if not scene_json.exists():
    raise SystemExit(f"❌ missing scene file: {scene_json}")

scenes = json.loads(scene_json.read_text(encoding="utf-8"))
if not scenes:
    raise SystemExit("❌ no scenes found")

candidates = []
target_min = 10.0
target_max = 20.0
ideal = 15.0

for i in range(len(scenes)):
    start = scenes[i]["start"]

    for j in range(i, len(scenes)):
        end = scenes[j]["end"]
        total = end - start

        if total < target_min:
            continue
        if total > target_max:
            break

        candidates.append({
            "scene_start_index": i,
            "scene_end_index": j,
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(total, 2),
            "scene_count": j - i + 1,
            "distance_from_ideal": round(abs(total - ideal), 2),
        })

candidates.sort(key=lambda x: (x["distance_from_ideal"], x["scene_count"]))

final_rows = []
used_windows = []

for row in candidates:
    a = row["start"]
    b = row["end"]

    overlap = False
    for x, y in used_windows:
        if max(a, x) < min(b, y):
            overlap = True
            break

    if overlap:
        continue

    used_windows.append((a, b))
    final_rows.append(row)

    if len(final_rows) >= 60:
        break

out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(final_rows, indent=2), encoding="utf-8")

print("✅ wrote", out_json)
print("COUNT", len(final_rows))
for i, row in enumerate(final_rows[:20], 1):
    print(i, row["start"], "->", row["end"], "dur", row["duration"], "| scenes", row["scene_count"])
