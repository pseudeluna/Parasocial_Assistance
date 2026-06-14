import re
from typing import Callable, Optional, Set

from pytubefix import YouTube, extract
from pytubefix.contrib.channel import Channel

CHECK_INTERVAL_SECONDS = 60
VIDEO_ID_LIMIT = 30

CHANNEL_URL_PATTERN = re.compile(
    r"^https?://(www\.)?(youtube\.com/(channel/|c/|user/|@)|youtu\.be/)",
    re.IGNORECASE,
)


def is_valid_channel_url(url: str) -> bool:
    return bool(CHANNEL_URL_PATTERN.match(url.strip()))


def get_channel_video_ids(channel_url: str, limit: int = VIDEO_ID_LIMIT) -> Set[str]:
    channel = Channel(channel_url.strip())
    _ = channel.videos
    video_ids: Set[str] = set()
    for index, url in enumerate(channel.video_urls):
        if index >= limit:
            break
        video_ids.add(extract.video_id(url))
    return video_ids


def download_video(
    video_url: str,
    quality: int,
    output_path: str,
    on_progress: Optional[Callable] = None,
) -> str:
    yt = YouTube(video_url, on_progress_callback=on_progress)
    if quality == 1:
        stream = yt.streams.get_lowest_resolution()
    else:
        stream = yt.streams.get_highest_resolution()

    if stream is None:
        raise RuntimeError(f"No downloadable stream found for {yt.title}")

    stream.download(output_path=output_path)
    return yt.title


def find_new_video_ids(channel_url: str, known_ids: Set[str]) -> list[str]:
    current_ids = get_channel_video_ids(channel_url)
    return [video_id for video_id in current_ids if video_id not in known_ids]


if __name__ == "__main__":
    from GUI import run_app

    run_app()
