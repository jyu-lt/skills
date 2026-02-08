---
name: fetch-youtube-transcript
description: Fetch and save YouTube video transcripts as plain text files using youtube-transcript-api with proxy support. Use when the user asks to get transcript/subtitle text from a YouTube video URL or video ID, export transcript text to a file, or automate transcript retrieval.
---

# YouTube Transcript Fetcher

Fetch a transcript with `scripts/yt_transcript.py`, then return the saved file path.

## Workflow

1. Resolve the target video ID from either a full YouTube URL (`youtube.com/watch?v=...`, `youtu.be/...`, `youtube.com/shorts/...`) or a raw video ID.
2. Confirm proxy credentials are available in `OXY_PROXY_URL`.
3. Run the script to fetch transcript chunks and write one line per chunk.
4. Return the output path and, when useful, a short excerpt.

## Commands

Install dependency:

```bash
python3 -m pip install youtube-transcript-api
```

Set proxy URL:

```bash
export OXY_PROXY_URL="http://username:password@proxy-host:proxy-port"
```

Fetch transcript to default output (`<video_id>.txt`):

```bash
python3 scripts/yt_transcript.py --video "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Fetch transcript to custom output:

```bash
python3 scripts/yt_transcript.py --video dQw4w9WgXcQ --output /tmp/transcript.txt
```

## Error Handling

- If `OXY_PROXY_URL` is missing, set it before running the script.
- If transcript fetching fails, verify the video ID is valid, transcripts are available for that video, and proxy credentials/connectivity are correct.
