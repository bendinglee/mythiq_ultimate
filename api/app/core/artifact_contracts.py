from __future__ import annotations

from typing import Any, Dict, List


def make_text_artifact(content: str) -> Dict[str, Any]:
    return {
        "artifact_type": "text_brief",
        "summary": " ".join(content.split())[:240],
        "artifact_data": {
            "content": content[:4000],
        },
        "next_stage_inputs": {
            "brief": " ".join(content.split())[:400],
        },
    }


def make_code_artifact(content: str) -> Dict[str, Any]:
    lines = content.splitlines()
    functions = []
    for line in lines:
        s = line.strip()
        if s.startswith("def "):
            functions.append(s.split("(")[0].replace("def ", "").strip())
    return {
        "artifact_type": "code_patch",
        "summary": " ".join(content.split())[:240],
        "artifact_data": {
            "functions": functions[:10],
            "language": "python",
            "content": content[:4000],
        },
        "next_stage_inputs": {
            "code_summary": " ".join(content.split())[:220],
            "functions": functions[:5],
        },
    }


def make_game_artifact(content: str) -> Dict[str, Any]:
    lines = [x.strip() for x in content.splitlines() if x.strip()]
    bullets = [x[2:].strip() for x in lines if x.startswith("- ")]
    return {
        "artifact_type": "game_design",
        "summary": " ".join(content.split())[:240],
        "artifact_data": {
            "systems": bullets[:8],
            "content": content[:4000],
        },
        "next_stage_inputs": {
            "game_summary": " ".join(content.split())[:220],
            "systems": bullets[:5],
        },
    }


def make_docs_artifact(content: str) -> Dict[str, Any]:
    lines = [x.strip() for x in content.splitlines() if x.strip()]
    headings = [x.lstrip("#").strip() for x in lines if x.startswith("#")][:8]
    bullets = [x[2:].strip() for x in lines if x.startswith("- ")][:8]
    return {
        "artifact_type": "docs_blueprint",
        "summary": " ".join(content.split())[:240],
        "artifact_data": {
            "headings": headings,
            "key_points": bullets,
            "content": content[:4000],
        },
        "next_stage_inputs": {
            "doc_summary": " ".join(headings[:5]),
            "key_points": bullets[:5],
        },
    }


def make_image_artifact(content: str) -> Dict[str, Any]:
    flat = " ".join(content.split())
    style = ""
    composition = ""
    for line in content.splitlines():
        s = line.strip()
        if s.lower().startswith("style:"):
            style = s.split(":", 1)[1].strip()
        if s.lower().startswith("composition:"):
            composition = s.split(":", 1)[1].strip()
    return {
        "artifact_type": "image_prompt_package",
        "summary": flat[:240],
        "artifact_data": {
            "style": style,
            "composition": composition,
            "content": content[:4000],
        },
        "next_stage_inputs": {
            "visual_summary": flat[:320],
            "style": style,
            "composition": composition,
        },
    }


def make_shorts_artifact(content: str) -> Dict[str, Any]:
    lines = [x.strip() for x in content.splitlines() if x.strip()]
    beats: List[str] = []
    for line in lines:
        if line[:2].isdigit() or line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or line.startswith("4.") or line.startswith("5."):
            beats.append(line)
    bullets = [x[2:].strip() for x in lines if x.startswith("- ")]
    return {
        "artifact_type": "shorts_blueprint",
        "summary": " ".join(content.split())[:240],
        "artifact_data": {
            "beats": beats[:8],
            "edit_notes": bullets[:8],
            "content": content[:4000],
        },
        "next_stage_inputs": {
            "hook_and_beats": " | ".join(beats[:5]),
            "edit_notes": bullets[:5],
        },
    }


def make_animation_artifact(content: str) -> Dict[str, Any]:
    lines = [x.strip() for x in content.splitlines() if x.strip()]
    shot_list = []
    for line in lines:
        if line.startswith("1.") or line.startswith("2.") or line.startswith("3.") or line.startswith("4.") or line.startswith("5."):
            shot_list.append(line)
    bullets = [x[2:].strip() for x in lines if x.startswith("- ")]
    return {
        "artifact_type": "animation_plan",
        "summary": " ".join(content.split())[:240],
        "artifact_data": {
            "shot_list": shot_list[:8],
            "notes": bullets[:8],
            "content": content[:4000],
        },
        "next_stage_inputs": {
            "shot_summary": " | ".join(shot_list[:5]),
            "notes": bullets[:5],
        },
    }


def build_artifact(feature: str, content: str) -> Dict[str, Any]:
    if feature == "code":
        return make_code_artifact(content)
    if feature == "game":
        return make_game_artifact(content)
    if feature == "docs":
        return make_docs_artifact(content)
    if feature == "image":
        return make_image_artifact(content)
    if feature == "shorts":
        return make_shorts_artifact(content)
    if feature == "animation":
        return make_animation_artifact(content)
    return make_text_artifact(content)
