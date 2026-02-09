#!/usr/bin/env python3
"""Download a source video with yt-dlp and render a YouTube Shorts 9:16 cut."""

from __future__ import annotations

import argparse
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


ANCHOR_EXPR = {
    "left": "0",
    "center": "(iw-ow)/2",
    "right": "iw-ow",
}

ANCHOR_CENTER_EXPR = {
    "left": "ow/2",
    "center": "iw/2",
    "right": "iw-ow/2",
}


def run(cmd: list[str], dry_run: bool = False) -> int:
    print("Command:")
    print(shlex.join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, check=False).returncode


def resolve_yt_dlp_cmd() -> list[str] | None:
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]

    module_check = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--version"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if module_check.returncode == 0:
        return [sys.executable, "-m", "yt_dlp"]
    return None


def parse_anchor_map(value: str, default_anchor: str) -> list[tuple[float, str]]:
    if not value:
        return []

    parsed: list[tuple[float, str]] = []
    for entry in value.split(","):
        item = entry.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid anchor-map entry: {item}")
        t_raw, anchor = item.split(":", 1)
        anchor = anchor.strip().lower()
        if anchor not in ANCHOR_EXPR:
            raise ValueError(f"Unsupported anchor '{anchor}' in anchor-map")
        parsed.append((float(t_raw.strip()), anchor))

    parsed.sort(key=lambda x: x[0])

    # Drop entries that match the default anchor at t=0 behavior.
    return [(t, a) for (t, a) in parsed if not (t <= 0 and a == default_anchor)]


def parse_x_map(value: str) -> list[tuple[float, float]]:
    if not value:
        return []

    parsed: list[tuple[float, float]] = []
    for entry in value.split(","):
        item = entry.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid x-map entry: {item}")
        t_raw, pos_raw = item.split(":", 1)
        t = float(t_raw.strip())
        pos = float(pos_raw.strip())
        if not (0.0 <= pos <= 1.0):
            raise ValueError(f"x-map position must be within [0.0, 1.0], got {pos}")
        parsed.append((t, pos))

    parsed.sort(key=lambda x: x[0])
    return parsed


def build_center_expr(default_anchor: str, anchor_map: list[tuple[float, str]], x_map: list[tuple[float, float]]) -> str:
    expr = ANCHOR_CENTER_EXPR[default_anchor]

    if x_map:
        for t, pos in x_map:
            expr = f"if(gte(t\\,{t})\\,{pos}*iw\\,{expr})"
        return expr

    for t, anchor in anchor_map:
        expr = f"if(gte(t\\,{t})\\,{ANCHOR_CENTER_EXPR[anchor]}\\,{expr})"
    return expr


def build_x_expr(center_expr: str) -> str:
    return f"clip(({center_expr})-ow/2\\,0\\,iw-ow)"


def pick_downloaded_source(out_dir: Path) -> Path:
    candidates = sorted(out_dir.glob("source.*"))
    candidates = [p for p in candidates if p.suffix.lower() not in {".part", ".tmp"}]
    if not candidates:
        raise FileNotFoundError("No downloaded source file found (expected source.<ext>)")
    return max(candidates, key=lambda p: p.stat().st_size)


def max_listed_height(
    yt_dlp_cmd: list[str],
    url: str,
    extractor_args: str,
    cookies_from_browser: str | None,
    dry_run: bool,
) -> int | None:
    cmd = [*yt_dlp_cmd, "-F", "--extractor-args", extractor_args, url]
    if cookies_from_browser:
        cmd[1:1] = ["--cookies-from-browser", cookies_from_browser]

    print("Command:")
    print(shlex.join(cmd))
    if dry_run:
        return None

    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        return None

    heights = [int(v) for v in re.findall(r"\b(\d{3,4})p\b", completed.stdout)]
    return max(heights) if heights else None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create a YouTube Shorts-ready vertical cut")
    p.add_argument("--url", required=True, help="YouTube/video URL")
    p.add_argument("--out-dir", default=".", help="Output folder")
    p.add_argument("--output", default="short_9x16.mp4", help="Output filename")
    p.add_argument("--start", type=float, default=0.0, help="Start time in seconds")
    p.add_argument("--duration", type=float, default=60.0, help="Duration in seconds")
    p.add_argument("--width", type=int, default=1080, help="Output width")
    p.add_argument("--height", type=int, default=1920, help="Output height")
    p.add_argument("--anchor", choices=["left", "center", "right"], default="center", help="Default crop anchor")
    p.add_argument(
        "--anchor-map",
        default="",
        help="Fallback time-based anchor shifts, e.g. '38.372:left,44.461:right'",
    )
    p.add_argument(
        "--x-map",
        default="",
        help="Preferred time-based focal x positions in [0..1], e.g. '4:0.38,20:0.66'",
    )
    p.add_argument("--extractor-args", default="youtube:player_client=ios,android,web_safari", help="yt-dlp extractor args")
    p.add_argument("--download-format", default="bv*+ba/b", help="yt-dlp format selector")
    p.add_argument("--cookies-from-browser", help="Optional browser name for authenticated pulls")
    p.add_argument("--video-crf", type=int, default=18, help="x264 CRF")
    p.add_argument("--video-preset", default="slow", help="x264 preset")
    p.add_argument("--audio-bitrate", default="192k", help="AAC bitrate")
    p.add_argument("--dry-run", action="store_true", help="Print commands only")
    return p


def main() -> int:
    args = build_parser().parse_args()

    yt_dlp_cmd = resolve_yt_dlp_cmd()
    if yt_dlp_cmd is None:
        print("yt-dlp is not installed (binary or python module).", file=sys.stderr)
        return 127
    if shutil.which("ffmpeg") is None and not args.dry_run:
        print("ffmpeg is not installed or not on PATH.", file=sys.stderr)
        return 127

    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    anchor_map = parse_anchor_map(args.anchor_map, args.anchor)
    x_map = parse_x_map(args.x_map)
    if x_map and anchor_map:
        print("Info: both --x-map and --anchor-map provided; using --x-map.", file=sys.stderr)
    center_expr = build_center_expr(args.anchor, anchor_map, x_map)
    x_expr = build_x_expr(center_expr)

    max_h = max_listed_height(yt_dlp_cmd, args.url, args.extractor_args, args.cookies_from_browser, args.dry_run)
    if max_h is not None and max_h <= 360:
        print("Warning: highest listed source format is 360p; output will be upscaled.", file=sys.stderr)

    source_template = out_dir / "source.%(ext)s"
    dl_cmd = [
        *yt_dlp_cmd,
        "--newline",
        "--extractor-args",
        args.extractor_args,
        "-S",
        "res,fps,codec:h264",
        "-f",
        args.download_format,
        "-o",
        str(source_template),
        args.url,
    ]
    if args.cookies_from_browser:
        dl_cmd[1:1] = ["--cookies-from-browser", args.cookies_from_browser]

    rc = run(dl_cmd, args.dry_run)
    if rc != 0:
        return rc

    source_path = out_dir / "source.mp4"
    if not args.dry_run:
        source_path = pick_downloaded_source(out_dir)

    vf = (
        f"scale=-2:{args.height}:flags=lanczos,"
        f"crop={args.width}:{args.height}:{x_expr}:0,"
        "unsharp=5:5:0.75:3:3:0.35,setsar=1,format=yuv420p"
    )

    output_path = out_dir / args.output
    ff_cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(args.start),
        "-i",
        str(source_path),
        "-t",
        str(args.duration),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        args.video_preset,
        "-crf",
        str(args.video_crf),
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-b:a",
        args.audio_bitrate,
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    rc = run(ff_cmd, args.dry_run)
    if rc != 0:
        return rc

    if args.dry_run:
        return 0

    probe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=index,codec_type,codec_name,width,height,sample_rate,channels",
        "-show_entries",
        "format=duration,size,bit_rate",
        "-of",
        "default=noprint_wrappers=1",
        str(output_path),
    ]
    print("Command:")
    print(shlex.join(probe_cmd))
    return subprocess.run(probe_cmd, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
