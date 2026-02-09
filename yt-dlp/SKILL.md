---
name: yt-dlp
description: Download, inspect, and transform online media with yt-dlp and ffmpeg, including AI-judged YouTube Shorts creation. Use when a user asks to fetch media from a URL, list formats before downloading, extract MP3/M4A audio, download captions, limit playlist ranges, or produce a high-engagement 9:16 short chosen from transcript content instead of arbitrary first-minute clips.
---

# yt-dlp

Use this skill for media download workflows and AI-led Shorts production.

## Core Principle

Treat scripts as execution tools only. The model must decide:

- which moment is most interesting,
- where the crop should focus over time,
- whether the result is visually coherent.

Do not delegate those judgments to fixed script heuristics.

## Mandatory AI Workflow for Shorts

1. Prepare transcript artifacts first (this must leverage the `fetch-youtube-transcript` skill):

```bash
python3 scripts/prepare_short_context.py --url "<URL>" --out-dir ./downloads/shorts
```

This runs `fetch-youtube-transcript` for plain text and writes a timed JSONL transcript.

2. Read the timed transcript and choose 2-3 candidate windows (45-60s) based on hook strength, standalone clarity, and novelty.
3. Pick one final window and justify why it is strongest.
4. Sample frames from that window (every 2-4s) and decide focal positions with AI judgment.
5. Render with explicit `--start`, `--duration`, and `--x-map`.
6. Validate output streams and loudness before finalizing.

## Crop Decision Rules (AI Judgment)

- Prefer candidate windows with stable shot grammar (single-speaker close-up or clean A/B cuts) over chaotic montage sections.
- For over-shoulder two-shots, keep the active speaker fully in frame and treat the passive speaker as optional context.
- Use `--x-map` as focal-center positions:
  - `~0.30-0.40` for left speaker close-up
  - `~0.60-0.70` for right speaker close-up
  - `~0.48-0.52` for centered UI/title cards
- Iterate render -> sample frames -> adjust `--x-map` until no speaker is clipped in key beats.
- If frequent clipping persists, choose a different transcript-selected segment rather than forcing a bad crop.

## Command Surface

General yt-dlp operations:

```bash
python3 scripts/yt_dlp_helper.py --url "<URL>" --mode inspect
python3 scripts/yt_dlp_helper.py --url "<URL>" --mode video --out-dir ./downloads
python3 scripts/yt_dlp_helper.py --url "<URL>" --mode audio --out-dir ./downloads/audio
python3 scripts/yt_dlp_helper.py --url "<URL>" --mode subs --subs-langs "en.*,es.*"
python3 scripts/yt_dlp_helper.py --url "<URL>" --mode playlist --playlist-items "1-20"
```

Render a Shorts clip from an AI-selected segment:

```bash
python3 scripts/make_youtube_short.py \
  --url "<URL>" \
  --out-dir ./downloads/shorts \
  --output short_9x16.mp4 \
  --start <SECONDS> \
  --duration <SECONDS> \
  --x-map "0:0.50,8:0.38,20:0.66"
```

`--x-map` uses normalized focal centers (`0.0` left edge, `1.0` right edge). Prefer this over coarse left/center/right anchors.

## Quality Gates

- Never default to `start=0` unless the user asks for the intro.
- Never ship a short without `ffprobe` verification of both video and audio streams.
- If source quality is limited (for example only 360p is available), state this clearly.
- Reject crops that clip speaker faces/body; adjust `--x-map` and re-render.
- Reject candidate windows that cannot pass framing quality after two `--x-map` iterations; pick a better moment from transcript.

## Resources

### scripts/

- `scripts/prepare_short_context.py`: Creates plain + timed transcript context (integrates with `fetch-youtube-transcript`).
- `scripts/make_youtube_short.py`: Download + transcode pipeline for Shorts rendering.
- `scripts/yt_dlp_helper.py`: General download helper (`inspect`, `video`, `audio`, `subs`, `playlist`).

### references/

- `references/command-patterns.md`: Direct command patterns and verification checks.
