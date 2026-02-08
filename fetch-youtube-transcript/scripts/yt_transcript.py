import argparse
import os
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig


def extract_video_id(video: str) -> str:
    """Return a YouTube video ID from either a raw ID or supported URL."""
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch YouTube video transcript")
    parser.add_argument(
        "--video",
        required=True,
        help="YouTube video URL or raw video ID",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (default: <video_id>.txt)",
    )
    args = parser.parse_args()

    video_id = extract_video_id(args.video)
    if not video_id:
        raise SystemExit("Unable to determine video ID from --video input.")

    output_file = args.output or f"{video_id}.txt"

    proxy_url = os.environ.get("OXY_PROXY_URL")
    if not proxy_url:
        raise SystemExit("Missing OXY_PROXY_URL environment variable.")

    ytt_api = YouTubeTranscriptApi(
        proxy_config=GenericProxyConfig(
            http_url=proxy_url,
            https_url=proxy_url,
        )
    )
    chunks = ytt_api.fetch(video_id)

    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(f"{chunk.text}\n")

    print(f"Transcript saved to {output_file}")


if __name__ == "__main__":
    main()
