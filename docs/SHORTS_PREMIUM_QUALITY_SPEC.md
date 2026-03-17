# Shorts Premium Quality Spec

## Goal
Produce vertical shorts that are:
- true 4K capable in premium mode
- story-first
- high-retention
- visually clean
- subtitle-safe
- packaging-ready

## Output tiers

### Tier A — Functional
- Correct vertical framing
- Clean export
- Basic subtitles
- No broken audio/video

### Tier B — Strong
- Strong opening hook
- Better pacing
- Cleaner subtitle grouping
- Fewer dead beats
- Better crop consistency

### Tier C — Premium
- 2160x3840 output in 4K mode
- Story arc: hook -> setup -> escalation -> payoff -> exit
- Smooth purposeful cuts
- No distracting transition spam
- Readable captions in safe zones
- Loudness-normalized speech
- Replay-friendly ending
- Export clean enough for sellable/client-facing delivery

## Hard pass/fail checks
- 4K mode must export 2160x3840
- No black frames at head/tail
- No silence block > 0.75s unless intentional
- First spoken/subtitle beat should land quickly
- No tracked generated project artifacts should dirty git
- Subtitles must report truthfully whether burned captions were applied
- Output file must exist and be non-trivial in size

## Story rules
Every short should aim to include:
1. Hook
2. Setup
3. Escalation
4. Payoff
5. Exit

## Transition policy
Default:
- hard cuts

Allowed only when useful:
- dip to black between major beats
- subtle zoom/punch for emphasis
- motion continuity easing

Not allowed:
- random flashy transitions
- transition spam
- effects that reduce clarity

## Caption rules
- Keep lines short
- Avoid caption collisions with UI-safe zones
- Group words by emphasis
- Highlight hook words selectively
- Prioritize readability over decoration

## Audio rules
- Speech first
- Normalize loudness
- Reduce obvious harshness/noise where possible
- Preserve clarity over loudness

## Quality scorecard
Rate 1-10:
- hook
- story
- pacing
- payoff
- captions
- transitions
- audio
- visual_finish
- replay_value
- platform_fit

Minimum premium target overall:
- 8.0+
