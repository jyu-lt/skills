#!/usr/bin/env python3
"""Prepare transcript artifacts so AI can choose the best Shorts moment and crop."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig


def run(cmd: list[str], dry_run: bool = False) -> int:
    print("Command:")
    print(shlex.join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, check=False).returncode


def extract_video_id(video: str) -> str:
    if "://" not in video and "/" not in video:
        return video

    parsed = urlparse(video)
    host = parsed.netloc.lower()

    if "youtu.be" in host:
        return parsed.path.strip("/").split("/")[0]

    if "youtube.com" in host:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [""])[0]
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/shorts/", 1)[1].split("/")[0]
        if parsed.path.startswith("/embed/"):
            return parsed.path.split("/embed/", 1)[1].split("/")[0]

    return video


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Prepare transcript context for AI-led Shorts decisions")
    p.add_argument("--url", required=True, help="YouTube URL or video ID")
    p.add_argument("--out-dir", default=".", help="Output directory")
    p.add_argument(
        "--fetch-script",
        default="~/.codex/skills/fetch-youtube-transcript/scripts/yt_transcript.py",
        help="Path to fetch-youtube-transcript script",
    )
    p.add_argument(
        "--plain-name",
        default="{video_id}_transcript.txt",
        help="Plain transcript filename template",
    )
    p.add_argument(
        "--timed-name",
        default="{video_id}_transcript_timed.jsonl",
        help="Timed transcript filename template",
    )
    p.add_argument("--skip-plain", action="store_true", help="Skip running fetch-youtube-transcript script")
    p.add_argument("--dry-run", action="store_true", help="Print commands and intended outputs only")
    return p


def main() -> int:
    args = build_parser().parse_args()

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    video_id = extract_video_id(args.url)
    if not video_id:
        print("Unable to determine YouTube video ID.", file=sys.stderr)
        return 2

    plain_path = out_dir / args.plain_name.format(video_id=video_id)
    timed_path = out_dir / args.timed_name.format(video_id=video_id)

    fetch_script = Path(args.fetch_script).expanduser()
    if not args.skip_plain:
        if not fetch_script.exists():
            print(f"fetch-youtube-transcript script not found: {fetch_script}", file=sys.stderr)
            return 2
        rc = run([sys.executable, str(fetch_script), "--video", args.url, "--output", str(plain_path)], args.dry_run)
        if rc != 0:
            return rc

    if args.dry_run:
        print(f"Would write timed transcript to: {timed_path}")
        return 0

    proxy_url = os.environ.get("OXY_PROXY_URL")
    if not proxy_url:
        print("Missing OXY_PROXY_URL environment variable.", file=sys.stderr)
        return 2

    api = YouTubeTranscriptApi(
        proxy_config=GenericProxyConfig(
            http_url=proxy_url,
            https_url=proxy_url,
        )
    )
    chunks = api.fetch(video_id)

    with open(timed_path, "w", encoding="utf-8") as f:
        for c in chunks:
            start = float(c.start)
            duration = float(c.duration)
            row = {
                "start": start,
                "duration": duration,
                "end": start + duration,
                "text": c.text,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Plain transcript: {plain_path}")
    print(f"Timed transcript: {timed_path}")
    print(f"Chunks: {len(chunks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
