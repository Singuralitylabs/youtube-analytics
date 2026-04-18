"""Cross-video endpoints: `/api/rankings` and `/api/compare`.

`/api/compare` is housed here (rather than under `/api/videos`) because it
operates across multiple videos, mirroring the rankings use case.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.collectors.youtube_analytics import HttpError as AnalyticsHttpError
from app.collectors.youtube_analytics import youtube_analytics_client
from app.collectors.youtube_data import HttpError as DataHttpError
from app.collectors.youtube_data import youtube_data_client
from app.schemas.responses import CompareItem, RankingItem

router = APIRouter(prefix="/api", tags=["rankings"])


_RANKING_METRICS = {
    "views",
    "estimatedMinutesWatched",
    "averageViewPercentage",
}
_COMPARE_METRICS = {
    "views",
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
}


def _map_analytics_error(err: AnalyticsHttpError) -> HTTPException:
    status = getattr(err, "status_code", None) or getattr(
        getattr(err, "resp", None), "status", 500
    )
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


@router.get("/rankings", response_model=list[RankingItem])
def get_rankings(
    metric: str = Query("views"),
    limit: int = Query(20, description="返す件数 (最大50)"),
    days: int = Query(30, description="直近何日分 (最大90)"),
) -> list[RankingItem]:
    """Return the top `limit` videos ranked by `metric` over the last `days`."""
    if metric not in _RANKING_METRICS:
        raise HTTPException(
            status_code=400,
            detail=(
                "metric は views / estimatedMinutesWatched / "
                "averageViewPercentage のいずれかです"
            ),
        )
    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=400,
            detail="limit は 1〜50 の範囲で指定してください",
        )
    _validate_days(days)

    try:
        rows = youtube_analytics_client.rankings(metric, limit, days)
    except AnalyticsHttpError as err:
        raise _map_analytics_error(err) from err

    if not rows:
        return []

    # Hydrate titles/published_at from Data API.
    video_ids = [row["video_id"] for row in rows]
    try:
        videos = youtube_data_client.get_videos(video_ids)
    except DataHttpError:
        videos = []
    meta = {v["video_id"]: v for v in videos}

    results: list[RankingItem] = []
    for idx, row in enumerate(rows, start=1):
        info = meta.get(row["video_id"], {})
        results.append(
            RankingItem(
                rank=idx,
                video_id=row["video_id"],
                title=info.get("title", ""),
                published_at=info.get("published_at", ""),
                value=row["value"],
            )
        )
    return results


@router.get("/compare", response_model=list[CompareItem])
def get_compare(
    ids: str = Query(..., description="動画IDをカンマ区切りで指定"),
    metric: str = Query("views"),
    days: int = Query(30, description="直近何日分 (最大90)"),
) -> list[CompareItem]:
    """Return per-day values of `metric` across the supplied video IDs."""
    video_ids = [v.strip() for v in ids.split(",") if v.strip()]
    if not video_ids:
        raise HTTPException(
            status_code=400,
            detail="ids は1つ以上の動画IDをカンマ区切りで指定してください",
        )
    if metric not in _COMPARE_METRICS:
        raise HTTPException(
            status_code=400,
            detail=(
                "metric は views / estimatedMinutesWatched / "
                "averageViewDuration / averageViewPercentage のいずれかです"
            ),
        )
    _validate_days(days)

    try:
        rows = youtube_analytics_client.compare(video_ids, metric, days)
    except AnalyticsHttpError as err:
        raise _map_analytics_error(err) from err

    try:
        videos = youtube_data_client.get_videos(video_ids)
    except DataHttpError:
        videos = []
    title_by_id = {v["video_id"]: v["title"] for v in videos}

    return [
        CompareItem(
            video_id=row["video_id"],
            title=title_by_id.get(row["video_id"], ""),
            date=row["date"],
            value=row["value"],
        )
        for row in rows
    ]
