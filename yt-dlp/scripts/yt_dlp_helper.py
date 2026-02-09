#!/usr/bin/env python3
"""Build and run common yt-dlp commands with predictable defaults."""

from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run yt-dlp with common presets")
    parser.add_argument("--url", required=True, help="Video or playlist URL")
    parser.add_argument(
        "--mode",
        choices=["inspect", "video", "audio", "subs", "playlist"],
        default="video",
        help="Preset workflow to use",
    )
    parser.add_argument("--out-dir", default=".", help="Output directory")
    parser.add_argument(
        "--filename-template",
        default="%(uploader)s/%(title)s [%(id)s].%(ext)s",
        help="yt-dlp output template",
    )
    parser.add_argument("--video-format", default="bv*+ba/b", help="Format selector for video modes")
    parser.add_argument("--audio-format", default="mp3", help="Audio format for extraction")
    parser.add_argument("--audio-quality", default="0", help="Audio quality for extraction")
    parser.add_argument("--subs-langs", default="en.*", help="Subtitle languages pattern")
    parser.add_argument("--playlist-items", help="Playlist item range, e.g. 1-20")
    parser.add_argument("--playlist-end", type=int, help="Last playlist index to download")
    parser.add_argument("--rate-limit", help="Rate limit, e.g. 2M")
    parser.add_argument("--archive-file", help="Path to download archive file")
    parser.add_argument("--cookies-from-browser", help="Browser name for auth cookies")
    parser.add_argument("--proxy", help="Proxy URL")
    parser.add_argument("--no-playlist", action="store_true", help="Force single-video behavior")
    parser.add_argument("--embed-metadata", action="store_true", help="Embed metadata")
    parser.add_argument("--embed-thumbnail", action="store_true", help="Embed thumbnail")
    parser.add_argument("--write-info-json", action="store_true", help="Write info JSON")
    parser.add_argument("--extra-arg", action="append", default=[], help="Extra raw yt-dlp arg")
    parser.add_argument("--dry-run", action="store_true", help="Print command without running")
    return parser


def build_command(args: argparse.Namespace) -> list[str]:
    out_dir = Path(args.out_dir).expanduser()
    output = out_dir / args.filename_template

    cmd = ["yt-dlp", "--newline", "-o", str(output)]

    if args.no_playlist:
        cmd.append("--no-playlist")

    if args.rate_limit:
        cmd.extend(["--limit-rate", args.rate_limit])

    if args.archive_file:
        cmd.extend(["--download-archive", args.archive_file])

    if args.cookies_from_browser:
        cmd.extend(["--cookies-from-browser", args.cookies_from_browser])

    if args.proxy:
        cmd.extend(["--proxy", args.proxy])

    if args.embed_metadata:
        cmd.append("--embed-metadata")

    if args.embed_thumbnail:
        cmd.append("--embed-thumbnail")

    if args.write_info_json:
        cmd.append("--write-info-json")

    if args.mode == "inspect":
        cmd.extend(["--no-download", "-F"])
    elif args.mode == "video":
        cmd.extend(["-f", args.video_format])
    elif args.mode == "audio":
        cmd.extend(["-x", "--audio-format", args.audio_format, "--audio-quality", args.audio_quality])
    elif args.mode == "subs":
        cmd.extend(["--skip-download", "--write-sub", "--write-auto-sub", "--sub-langs", args.subs_langs])
    elif args.mode == "playlist":
        cmd.extend(["--yes-playlist", "-f", args.video_format])
        if args.playlist_items:
            cmd.extend(["--playlist-items", args.playlist_items])
        if args.playlist_end:
            cmd.extend(["--playlist-end", str(args.playlist_end)])

    if args.extra_arg:
        cmd.extend(args.extra_arg)

    cmd.append(args.url)
    return cmd


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if shutil.which("yt-dlp") is None and not args.dry_run:
        print("yt-dlp is not installed or not on PATH.", file=sys.stderr)
        return 127

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = build_command(args)
    print("Command:")
    print(shlex.join(cmd))

    if args.dry_run:
        return 0

    completed = subprocess.run(cmd, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
