"""YouTube Analytics API client (OAuth 2.0 auth)."""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import get_settings


OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def load_credentials() -> Credentials:
    """Load OAuth credentials from the local token file, refreshing if needed."""
    settings = get_settings()
    token_path = settings.TOKEN_FILE
    if not os.path.exists(token_path):
        raise FileNotFoundError(
            f"OAuth token '{token_path}' が見つかりません。"
            "scripts/setup_oauth.py を先に実行してください。"
        )

    creds = Credentials.from_authorized_user_file(token_path, OAUTH_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w", encoding="utf-8") as fp:
            fp.write(creds.to_json())
    return creds


def _date_range(days: int) -> tuple[str, str]:
    """Return (start_date, end_date) as YYYY-MM-DD for a trailing window."""
    end = date.today()
    start = end - timedelta(days=days - 1 if days > 0 else 0)
    return start.isoformat(), end.isoformat()


class YouTubeAnalyticsClient:
    """Wrapper over the YouTube Analytics API (reports.query)."""

    def __init__(self) -> None:
        self._service: Any | None = None

    def _build(self) -> Any:
        if self._service is None:
            creds = load_credentials()
            self._service = build(
                "youtubeAnalytics",
                "v2",
                credentials=creds,
                cache_discovery=False,
            )
        return self._service

    def _query(self, **kwargs: Any) -> dict[str, Any]:
        """Execute a `reports.query` call with `ids='channel==MINE'`."""
        service = self._build()
        params: dict[str, Any] = {"ids": "channel==MINE", **kwargs}
        return service.reports().query(**params).execute()

    def video_timeseries(
        self, video_id: str, metric: str, days: int
    ) -> list[dict[str, Any]]:
        """Per-day values for a single metric of a given video."""
        start, end = _date_range(days)
        resp = self._query(
            startDate=start,
            endDate=end,
            metrics=metric,
            dimensions="day",
            filters=f"video=={video_id}",
            sort="day",
        )
        rows = resp.get("rows") or []
        return [{"date": row[0], "value": float(row[1])} for row in rows]

    def traffic_sources(
        self, video_id: str, days: int
    ) -> list[dict[str, Any]]:
        """Traffic-source breakdown for a video."""
        start, end = _date_range(days)
        resp = self._query(
            startDate=start,
            endDate=end,
            metrics="views",
            dimensions="insightTrafficSourceType",
            filters=f"video=={video_id}",
            sort="-views",
        )
        rows = resp.get("rows") or []
        return [
            {"traffic_source_type": row[0], "views": int(row[1])}
            for row in rows
        ]

    def demographics(
        self, video_id: str, days: int
    ) -> list[dict[str, Any]]:
        """Age/gender viewer breakdown for a video."""
        start, end = _date_range(days)
        resp = self._query(
            startDate=start,
            endDate=end,
            metrics="viewerPercentage",
            dimensions="ageGroup,gender",
            filters=f"video=={video_id}",
        )
        rows = resp.get("rows") or []
        return [
            {
                "age_group": row[0],
                "gender": row[1],
                "view_percentage": float(row[2]),
            }
            for row in rows
        ]

    def rankings(
        self, metric: str, limit: int, days: int
    ) -> list[dict[str, Any]]:
        """Video ranking rows sorted by the given metric (descending)."""
        start, end = _date_range(days)
        resp = self._query(
            startDate=start,
            endDate=end,
            metrics=metric,
            dimensions="video",
            sort=f"-{metric}",
            maxResults=limit,
        )
        rows = resp.get("rows") or []
        return [
            {"video_id": row[0], "value": float(row[1])}
            for row in rows
        ]

    def top_videos(
        self, days: int, limit: int = 50, sort: str = "-views"
    ) -> list[dict[str, Any]]:
        """Top videos with views, watch-time, avg duration AND retention in one call.

        Unlike ``rankings(metric=...)``, this multi-metric query is supported for
        ``averageViewDuration`` / ``averageViewPercentage`` because they ride
        along as columns rather than being the sort key (sorting by those metrics
        with ``dimensions=video`` returns 400/500). ``sort`` must be a supported
        key such as ``-views`` or ``-estimatedMinutesWatched``.
        """
        start, end = _date_range(days)
        resp = self._query(
            startDate=start,
            endDate=end,
            metrics=(
                "views,estimatedMinutesWatched,"
                "averageViewDuration,averageViewPercentage"
            ),
            dimensions="video",
            sort=sort,
            maxResults=limit,
        )
        headers = [h["name"] for h in resp.get("columnHeaders", [])]
        rows = resp.get("rows") or []
        result: list[dict[str, Any]] = []
        for row in rows:
            rec = dict(zip(headers, row))
            result.append(
                {
                    "video_id": rec.get("video", ""),
                    "views": int(rec.get("views", 0) or 0),
                    "minutes": int(rec.get("estimatedMinutesWatched", 0) or 0),
                    "avg_view_sec": round(float(rec.get("averageViewDuration", 0) or 0), 1),
                    "retention_pct": round(
                        float(rec.get("averageViewPercentage", 0) or 0), 1
                    ),
                }
            )
        return result

    def compare(
        self, video_ids: list[str], metric: str, days: int
    ) -> list[dict[str, Any]]:
        """Per-day values of a metric across multiple videos."""
        if not video_ids:
            return []
        start, end = _date_range(days)
        filter_expr = f"video=={','.join(video_ids)}"
        resp = self._query(
            startDate=start,
            endDate=end,
            metrics=metric,
            dimensions="day,video",
            filters=filter_expr,
            sort="day",
        )
        rows = resp.get("rows") or []
        return [
            {"date": row[0], "video_id": row[1], "value": float(row[2])}
            for row in rows
        ]


youtube_analytics_client = YouTubeAnalyticsClient()

__all__ = [
    "YouTubeAnalyticsClient",
    "youtube_analytics_client",
    "load_credentials",
    "OAUTH_SCOPES",
    "HttpError",
]
