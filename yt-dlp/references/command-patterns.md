# yt-dlp and Shorts Command Patterns

Use these commands as building blocks. Keep selection and framing decisions with AI judgment.

## Inspect Available Formats

```bash
yt-dlp --no-download -F "<URL>"
```

## General Downloads

```bash
yt-dlp -f "bv*+ba/b" -o "downloads/%(uploader)s/%(title)s [%(id)s].%(ext)s" "<URL>"
yt-dlp -x --audio-format mp3 --audio-quality 0 -o "downloads/audio/%(title)s.%(ext)s" "<URL>"
yt-dlp --skip-download --write-sub --write-auto-sub --sub-langs "en.*,es.*" "<URL>"
```

## Prepare Transcript Context (Required for Shorts)

```bash
python3 scripts/prepare_short_context.py --url "<URL>" --out-dir ./downloads/shorts
```

Outputs:
- `<video_id>_transcript.txt`
- `<video_id>_transcript_timed.jsonl`

## Sample Frames for Crop Decisions

```bash
ffmpeg -y -ss <START_SECONDS> -i source.mp4 -frames:v 1 frame.jpg
```

Run every 2-4s over the candidate window and set `--x-map` accordingly.

## Render Shorts With AI-Chosen Segment and Focus Map

```bash
python3 scripts/make_youtube_short.py \
  --url "<URL>" \
  --out-dir ./downloads/shorts \
  --output short_9x16.mp4 \
  --start <SECONDS> \
  --duration <SECONDS> \
  --x-map "0:0.50,8:0.38,20:0.66,32:0.40,36:0.64"
```

## Verify Output

```bash
ffprobe -v error \
  -show_entries stream=index,codec_type,codec_name,width,height,sample_rate,channels \
  -show_entries format=duration,size,bit_rate \
  -of default=noprint_wrappers=1 short_9x16.mp4

ffmpeg -i short_9x16.mp4 -af volumedetect -f null -
```

## Reliability Notes

- YouTube may expose only low-resolution formats without valid auth/PO tokens.
- Use `--cookies-from-browser <browser>` only with user approval.
- If format ceilings are low, state that output is upscaled from source.
