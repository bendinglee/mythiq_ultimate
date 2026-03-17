# Mythiq YouTube Shorts / Compilation Feature — Master Spec

## Goal
Build a best-in-class long-video-to-short-video system that can:
- generate strong shorts from one long video
- generate montage / compilation shorts from 10+ source videos
- generate multiple style variants per clip
- generate relevant titles and descriptions automatically
- support any niche / sector / content type
- produce outputs that are fast to review and ready to export

## Core Modes

### 1. Single Long Video → Shorts
Input:
- one long source video
Output:
- 3 to 20 short clips
- each clip has a clean hook, conflict, payoff
- each clip has title, short description, anchor text, transcript

### 2. Multi-Video Montage / Compilation
Input:
- 2 to 20 source videos
Output:
- themed compilation shorts
- strongest moments merged into one coherent short
- can be chronological, highlight, funniest, most intense, educational, etc.

### 3. Clip Variants
For every chosen short:
- Variant A = safer / clearer / cleaner
- Variant B = more aggressive / stronger hook / more replayable
- optional Variant C later = experimental

## Primary Quality Goals
1. Best hook
2. Source relevance
3. Smooth pacing
4. Strong vertical framing
5. Clear narrative shape
6. Strong replayability
7. Professional polish
8. Relevant title + relevant description

## What “best in world for use” means
- minimal setup
- fast outputs
- understandable controls
- predictable quality
- niche aware
- title/description quality is built-in
- good enough to use daily without babysitting

## UX Controls for This Section
- Source mode: single / multi-video
- Genre: auto / gaming / commentary / education / story / podcast / finance / sports / music / documentary / custom
- Clip length: auto / 15 / 20 / 30 / 45 / 60
- Hook mode: auto / high-drama / curiosity / educational / emotional / funny / urgent
- Include moments prompt
- Exclude moments prompt
- Processing timeframe
- Style preset
- Output count
- Montage mode on/off
- Title style
- Description style

## Outputs Per Short
Each generated short must include:
- video file
- title
- description
- anchor_text
- transcript
- variant label
- score
- relevance
- suggested hashtags later

## Quality Contract
Reject clips that fail these:
- no real hook in first 3 seconds
- low source relevance
- muddy or repetitive transcript
- weak emotional turn
- bad pacing
- visually confusing framing

## Current Known Constraint
Caption burn is tooling-constrained on current ffmpeg build.
Short-term rule:
- captions are optional in renderer
- transcript, anchor, title, description still required
- subtitle pipeline can be swapped later without changing selection engine

## Definition of Done for This Feature
This feature is good enough to move on when:
- single-video mode works consistently
- multi-video montage mode exists
- title generation is relevant
- description generation is relevant
- scoring/eval loop improves quality over time
- outputs are fast to review/export
