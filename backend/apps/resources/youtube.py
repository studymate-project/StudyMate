"""YouTube URL parsing helpers for video resources."""

import re
from urllib.parse import parse_qs, urlsplit

from django.core.exceptions import ValidationError


YOUTUBE_VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})
YOUTUBE_SHORT_HOSTS = frozenset({"youtu.be", "www.youtu.be"})


def normalize_youtube_video_id(value: str, *, allow_raw_video_id: bool = True) -> str:
    """Return a canonical YouTube video ID from an ID or supported YouTube URL.

    Only standard watch, short-link, and embed URLs are accepted.  This keeps
    embed markup and arbitrary third-party URLs out of the stored video field.
    """

    if not isinstance(value, str):
        raise ValidationError("Provide a YouTube video ID or URL.")

    candidate = value.strip()
    if allow_raw_video_id and YOUTUBE_VIDEO_ID_PATTERN.fullmatch(candidate):
        return candidate

    try:
        parsed = urlsplit(candidate)
    except ValueError as error:
        raise ValidationError("Provide a valid YouTube URL.") from error

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValidationError("Provide a YouTube video ID or a valid YouTube URL.")
    try:
        has_port = parsed.port is not None
    except ValueError as error:
        raise ValidationError("Provide a valid YouTube URL.") from error
    if parsed.username or parsed.password or has_port:
        raise ValidationError("Provide a standard YouTube URL.")

    host = parsed.hostname.lower().rstrip(".")
    path_parts = [part for part in parsed.path.split("/") if part]

    if host in YOUTUBE_SHORT_HOSTS and len(path_parts) == 1:
        video_id = path_parts[0]
    elif host in YOUTUBE_HOSTS and path_parts == ["watch"]:
        video_ids = parse_qs(parsed.query).get("v", [])
        if len(video_ids) != 1:
            raise ValidationError("A YouTube watch URL must include one video ID.")
        video_id = video_ids[0]
    elif host in YOUTUBE_HOSTS and len(path_parts) == 2 and path_parts[0] == "embed":
        video_id = path_parts[1]
    else:
        raise ValidationError("Provide a supported YouTube video URL.")

    if not YOUTUBE_VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValidationError("Provide a valid 11-character YouTube video ID.")
    return video_id
