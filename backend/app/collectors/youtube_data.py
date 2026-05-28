"""YouTube Data API v3 client (API key auth)."""

from __future__ import annotations

import re
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import get_settings


# ISO 8601 duration → seconds (e.g. PT1H2M3S).
_DURATION_RE = re.compile(
    r"^PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?$"
)


def _iso8601_to_seconds(duration: str) -> int:
    """Convert an ISO 8601 duration string to total seconds."""
    if not duration:
        return 0
    match = _DURATION_RE.match(duration)
    if not match:
        return 0
    hours = int(match.group("h") or 0)
    minutes = int(match.group("m") or 0)
    seconds = int(match.group("s") or 0)
    return hours * 3600 + minutes * 60 + seconds


class YouTubeDataClient:
    """Thin wrapper around the YouTube Data API v3 (API-key auth)."""

    def __init__(self) -> None:
        self._service: Any | None = None

    def _build(self) -> Any:
        """Lazily construct the discovery client so imports stay cheap."""
        if self._service is None:
            settings = get_settings()
            self._service = build(
                "youtube",
                "v3",
                developerKey=settings.YOUTUBE_API_KEY,
                cache_discovery=False,
            )
        return self._service

    def get_channel_stats(self, channel_id: str) -> dict[str, int | str]:
        """Return headline stats for the given channel."""
        service = self._build()
        response = service.channels().list(
            part="statistics",
            id=channel_id,
        ).execute()

        items = response.get("items") or []
        if not items:
            raise LookupError(f"channel_id '{channel_id}' が見つかりません")

        stats = items[0].get("statistics", {})
        return {
            "channel_id": channel_id,
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "total_view_count": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
        }

    def get_channel_title(self, channel_id: str) -> str:
        """Return the channel's display title (empty string if not found)."""
        service = self._build()
        response = service.channels().list(
            part="snippet",
            id=channel_id,
        ).execute()
        items = response.get("items") or []
        if not items:
            return ""
        return items[0].get("snippet", {}).get("title", "")

    def list_video_ids(self, channel_id: str) -> list[str]:
        """Return all video IDs uploaded to the channel."""
        service = self._build()
        channel_resp = service.channels().list(
            part="contentDetails",
            id=channel_id,
        ).execute()

        items = channel_resp.get("items") or []
        if not items:
            raise LookupError(f"channel_id '{channel_id}' が見つかりません")

        uploads_id = (
            items[0]
            .get("contentDetails", {})
            .get("relatedPlaylists", {})
            .get("uploads")
        )
        if not uploads_id:
            return []

        video_ids: list[str] = []
        page_token: str | None = None
        while True:
            resp = service.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_id,
                maxResults=50,
                pageToken=page_token,
            ).execute()

            for item in resp.get("items", []):
                vid = item.get("contentDetails", {}).get("videoId")
                if vid:
                    video_ids.append(vid)

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return video_ids

    def get_videos(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """Return hydrated video records for the given IDs."""
        if not video_ids:
            return []

        service = self._build()
        results: list[dict[str, Any]] = []
        # Data API allows up to 50 IDs per call.
        for start in range(0, len(video_ids), 50):
            chunk = video_ids[start : start + 50]
            resp = service.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(chunk),
            ).execute()

            for item in resp.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                content = item.get("contentDetails", {})
                published = (snippet.get("publishedAt") or "")[:10]
                results.append(
                    {
                        "video_id": item.get("id", ""),
                        "title": snippet.get("title", ""),
                        "published_at": published,
                        "duration_sec": _iso8601_to_seconds(
                            content.get("duration", "")
                        ),
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                    }
                )
        return results

    def get_video(self, video_id: str) -> dict[str, Any]:
        """Return a single video record or raise `LookupError` if missing."""
        videos = self.get_videos([video_id])
        if not videos:
            raise LookupError(f"video_id '{video_id}' が見つかりません")
        return videos[0]


# Shared singleton used by routers.
youtube_data_client = YouTubeDataClient()

# Re-export for ergonomic `except` handling in routers.
__all__ = ["YouTubeDataClient", "youtube_data_client", "HttpError"]
