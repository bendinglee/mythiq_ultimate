# sidemen_scene_pipeline recovery status

## Current state
- final_selects are valid and preserved
- reports exist
- web review HTML exists
- original full scene_renders are missing
- remaining scene_renders/01_scene.mp4 is invalid/tiny
- original long source video required for rerender is not present in local cache

## Operational rule
Do not use this run for:
- rerender from source
- existing-scene replay

Use this run only for:
- reviewing exported final selects
- packaging/report reference
- archival recovery

## To fully restore reproducibility
Need one of:
1. original source video with duration >= ~5829.8s
2. restored full scene_renders set (01_scene.mp4 through 10_scene.mp4 or equivalent valid set)
