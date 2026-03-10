#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "mythiq" / "examples"
RESULTS = ROOT / "mythiq" / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

def save(name: str, data: dict) -> None:
    out = RESULTS / name
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"✅ wrote {out}")

def build_video_to_shorts() -> None:
    inp = json.loads((EXAMPLES / "video_input_minecraft_server.json").read_text(encoding="utf-8"))
    data = {
        "flow_id": "flow.video_to_shorts",
        "source_title": inp["title"],
        "source_url": inp["source_url"],
        "niche": inp["niche"],
        "target_platforms": inp["target_platforms"],
        "clips": [
            {
                "rank": 1,
                "clip_id": "clip_01",
                "hook": "I joined the biggest Minecraft server and it instantly turned into chaos.",
                "start_hint": "00:00",
                "end_hint": "00:28",
                "why_it_works": "Immediate scale, curiosity, and fast escalation.",
                "title": "I Joined Minecraft’s Biggest Server",
                "caption": "The first minutes were absolute chaos. #minecraft #shorts",
                "thumbnail_concept": "Player tiny against a giant crowded Minecraft server world with bold text: BIGGEST SERVER",
                "edit_notes": [
                    "Open on strongest visual of server scale",
                    "Hard cuts every 1.5-2.5 seconds",
                    "Use zoom on reaction moments"
                ],
                "retention_score": 92
            },
            {
                "rank": 2,
                "clip_id": "clip_02",
                "hook": "I thought I was prepared until the server completely overwhelmed me.",
                "start_hint": "00:29",
                "end_hint": "00:55",
                "why_it_works": "Personal emotion and pressure keep people watching.",
                "title": "I Was Not Ready For This Server",
                "caption": "This server was way bigger and crazier than I expected. #minecraft",
                "thumbnail_concept": "Overwhelmed player face with crowded server background and warning text",
                "edit_notes": [
                    "Start with confusion or panic beat",
                    "Keep captions large and centered",
                    "Add bass hit on reveal moment"
                ],
                "retention_score": 88
            },
            {
                "rank": 3,
                "clip_id": "clip_03",
                "hook": "Then everything suddenly escalated.",
                "start_hint": "00:56",
                "end_hint": "01:20",
                "why_it_works": "Escalation and payoff are strong short-form structure.",
                "title": "Then It Got Worse",
                "caption": "This is where the server got out of control. #gaming #minecraftshorts",
                "thumbnail_concept": "Explosive scene, motion blur, red arrows, dramatic text",
                "edit_notes": [
                    "Fast montage pacing",
                    "Use whoosh transitions sparingly",
                    "End on cliffhanger or payoff"
                ],
                "retention_score": 84
            },
            {
                "rank": 4,
                "clip_id": "clip_04",
                "hook": "This was the craziest moment on the whole server.",
                "start_hint": "01:21",
                "end_hint": "01:48",
                "why_it_works": "Best-moment framing gives a clear reason to stay.",
                "title": "Craziest Moment On The Server",
                "caption": "This one moment changed everything. #minecraft #viralshorts",
                "thumbnail_concept": "Peak action frame with circle highlight and bold white text",
                "edit_notes": [
                    "Front-load the payoff",
                    "Subtitle every spoken line",
                    "Use 9:16 crop with subject always centered"
                ],
                "retention_score": 86
            },
            {
                "rank": 5,
                "clip_id": "clip_05",
                "hook": "I finally understood why this server is legendary.",
                "start_hint": "01:49",
                "end_hint": "02:15",
                "why_it_works": "Resolution and meaning work well as a final short.",
                "title": "Now I Get The Hype",
                "caption": "After this, I understood why everyone talks about this server. #minecraft",
                "thumbnail_concept": "Hero shot of the world with awe-focused text",
                "edit_notes": [
                    "Use calmer pacing",
                    "Let payoff breathe for 1-2 seconds",
                    "Close with memorable line"
                ],
                "retention_score": 80
            }
        ]
    }
    save("video_to_shorts.output.json", data)

def build_explainer_text() -> None:
    data = {
        "flow_id": "flow.explainer_text",
        "topic": "Nikola Tesla free energy theory and in practice",
        "mode": "myth_vs_reality",
        "summary": (
            "Tesla explored wireless power transmission and radiant energy ideas, but this should not be confused "
            "with a proven machine that creates unlimited energy from nothing. The strongest practical side of his work "
            "was electrical engineering, especially AC power systems, high-frequency experiments, and wireless transmission concepts."
        ),
        "core_points": [
            "Tesla investigated energy capture and wireless transmission concepts.",
            "People often overstate these ideas as proof of limitless free energy.",
            "In practice, the real historical value lies in transmission, resonance, and electrical engineering."
        ],
        "established": [
            "Tesla made foundational contributions to alternating current systems.",
            "Tesla experimented with wireless transmission and high-voltage electrical effects.",
            "Tesla patented radiant energy concepts and discussed capturing environmental energy."
        ],
        "speculative_or_contested": [
            "Claims that Tesla built a proven limitless free-energy machine are not established engineering fact.",
            "Modern internet narratives often blend real patents with exaggerated conclusions."
        ],
        "in_practice": [
            "Practical discussion should focus on wireless power experiments, resonance, and transmission efficiency.",
            "A truthful explainer separates historical patents from unverified modern claims."
        ],
        "video_script": {
            "hook": "Did Nikola Tesla really discover free energy, or has the internet turned a real idea into a myth?",
            "intro": "Tesla was a brilliant inventor whose work changed electricity forever. But when people talk about Tesla and free energy, the truth is more complicated.",
            "body": [
                "Tesla absolutely explored ways to collect and transmit energy in unusual ways, including radiant energy and wireless power concepts.",
                "But that is not the same thing as proving a machine that creates limitless usable power from nothing.",
                "The real practical side of Tesla’s work is much more grounded: resonance, high-frequency electricity, AC systems, and wireless transmission experiments."
            ],
            "ending": "So the truth is this: Tesla pushed electrical science forward in extraordinary ways, but the strongest evidence supports engineering innovation, not a confirmed limitless free-energy device."
        },
        "titles": [
            "Tesla Free Energy: Myth vs Reality",
            "What Tesla Actually Meant By Free Energy",
            "Tesla’s Free Energy Theory Explained Honestly"
        ]
    }
    save("explainer_text.output.json", data)

def build_game_pack_builder() -> None:
    data = {
        "flow_id": "flow.game_pack_builder",
        "game_name": "Mythiq Football Pack Clash",
        "core_loop": [
            "Earn coins from matches and challenges",
            "Open packs to collect footballers",
            "Build stronger squads and unlock harder content"
        ],
        "currencies": ["coins"],
        "rarities": [
            {"name": "common", "weight": 60},
            {"name": "rare", "weight": 28},
            {"name": "epic", "weight": 10},
            {"name": "icon", "weight": 2}
        ],
        "screens": ["home", "packs", "reveal", "inventory", "squad", "collection", "store"],
        "pack_types": [
            {"name": "bronze pack", "cost": 500, "slots": 3},
            {"name": "silver pack", "cost": 1500, "slots": 4},
            {"name": "elite pack", "cost": 5000, "slots": 5}
        ],
        "systems": {
            "inventory": "Player cards are stored locally with rarity, position, club, nation, and rating.",
            "squad_building": "Users place cards into formation slots for attack, midfield, defense, and goalkeeper.",
            "chemistry": "Shared club, nation, or league gives a squad bonus.",
            "save_data": "Offline save file using local JSON storage."
        },
        "animation_plan": [
            "Pack shake before reveal",
            "Card glow by rarity color tier",
            "Slow spotlight for epic and icon pulls",
            "Quick summary screen after reveal"
        ],
        "phaser_notes": [
            "Use a weighted RNG table for rarity pulls",
            "Keep all pack open logic in one pure function",
            "Separate UI scenes: HomeScene, PackScene, RevealScene, SquadScene",
            "Use JSON data for player database and pack odds"
        ],
        "next_files": [
            "src/scenes/HomeScene.js",
            "src/scenes/PackScene.js",
            "src/scenes/RevealScene.js",
            "src/scenes/SquadScene.js",
            "src/data/players.json",
            "src/data/packs.json",
            "src/lib/openPack.js"
        ]
    }
    save("game_pack_builder.output.json", data)

def main() -> None:
    build_video_to_shorts()
    build_explainer_text()
    build_game_pack_builder()
    print("✅ all demo outputs generated")

if __name__ == "__main__":
    main()
