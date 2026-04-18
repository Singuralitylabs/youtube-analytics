"""Video-level endpoints (list, detail, timeseries, traffic, demographics)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from app.collectors.youtube_analytics import HttpError as AnalyticsHttpError
from app.collectors.youtube_analytics import youtube_analytics_client
from app.collectors.youtube_data import HttpError as DataHttpError
from app.collectors.youtube_data import youtube_data_client
from app.schemas.responses import (
    Demographic,
    TrafficSource,
    VideoDetail,
    VideoSummary,
    VideoTimeseriesPoint,
)
from config.settings import get_settings

router = APIRouter(prefix="/api/videos", tags=["videos"])


_TIMESERIES_METRICS = {
    "views",
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
}


def _map_data_error(err: DataHttpError) -> HTTPException:
    status = getattr(err, "status_code", None) or getattr(
        getattr(err, "resp", None), "status", 500
    )
    if status == 404:
        return HTTPException(status_code=404, detail="リソースが見つかりません")
    if status == 403:
        return HTTPException(
            status_code=429,
            detail="YouTube API のクォータ上限に達しました",
        )
    return HTTPException(status_code=500, detail="YouTube API 障害が発生しました")


def _map_analytics_error(err: AnalyticsHttpError) -> HTTPException:
    status = getattr(err, "status_code", None) or getattr(
        getattr(err, "resp", None), "status", 500
    )
    if status == 404:
        return HTTPException(status_code=404, detail="リソースが見つかりません")
    if status == 403:
        return HTTPException(
            status_code=429,
            detail="YouTube Analytics API のクォータ上限に達しました",
        )
    return HTTPException(
        status_code=500,
        detail="YouTube Analytics API 障害が発生しました",
    )


def _validate_days(days: int, *, maximum: int = 90) -> None:
    if days < 1 or days > maximum:
        raise HTTPException(
            status_code=400,
            detail=f"days は 1〜{maximum} の範囲で指定してください",
        )


@router.get("", response_model=list[VideoSummary])
def list_videos() -> list[VideoSummary]:
    """Return every uploaded video with its current counts."""
    settings = get_settings()
    try:
        video_ids = youtube_data_client.list_video_ids(settings.CHANNEL_ID)
        videos = youtube_data_client.get_videos(video_ids)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except DataHttpError as err:
        raise _map_data_error(err) from err

    return [
        VideoSummary(
            video_id=v["video_id"],
            title=v["title"],
            published_at=v["published_at"],
            view_count=v["view_count"],
            like_count=v["like_count"],
            comment_count=v["comment_count"],
        )
        for v in videos
    ]


@router.get("/{video_id}", response_model=VideoDetail)
def get_video(
    video_id: str = Path(..., description="YouTube 動画ID"),
) -> VideoDetail:
    """Return detailed info for a single video."""
    try:
        video = youtube_data_client.get_video(video_id)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except DataHttpError as err:
        raise _map_data_error(err) from err
    return VideoDetail(**video)


@router.get(
    "/{video_id}/timeseries",
    response_model=list[VideoTimeseriesPoint],
)
def get_video_timeseries(
    video_id: str = Path(..., description="YouTube 動画ID"),
    metric: str = Query("views"),
    days: int = Query(30, description="直近何日分 (最大90)"),
) -> list[VideoTimeseriesPoint]:
    """Return per-day values of a single Analytics metric for the video."""
    if metric not in _TIMESERIES_METRICS:
        raise HTTPException(
            status_code=400,
            detail=(
                "metric は views / estimatedMinutesWatched / "
                "averageViewDuration / averageViewPercentage のいずれかです"
            ),
        )
    _validate_days(days)

    try:
        rows = youtube_analytics_client.video_timeseries(
            video_id, metric, days
        )
    except AnalyticsHttpError as err:
        raise _map_analytics_error(err) from err
    return [VideoTimeseriesPoint(**row) for row in rows]


@router.get("/{video_id}/traffic", response_model=list[TrafficSource])
def get_video_traffic(
    video_id: str = Path(..., description="YouTube 動画ID"),
    days: int = Query(30, description="直近何日分 (最大90)"),
) -> list[TrafficSource]:
    """Return traffic-source breakdown for the given video."""
    _validate_days(days)

    try:
        rows = youtube_analytics_client.traffic_sources(video_id, days)
    except AnalyticsHttpError as err:
        raise _map_analytics_error(err) from err
    return [TrafficSource(**row) for row in rows]


@router.get("/{video_id}/demographics", response_model=list[Demographic])
def get_video_demographics(
    video_id: str = Path(..., description="YouTube 動画ID"),
    days: int = Query(30, description="直近何日分 (最大90)"),
) -> list[Demographic]:
    """Return age/gender viewer breakdown for the given video."""
    _validate_days(days)

    try:
        rows = youtube_analytics_client.demographics(video_id, days)
    except AnalyticsHttpError as err:
        raise _map_analytics_error(err) from err
    return [Demographic(**row) for row in rows]
