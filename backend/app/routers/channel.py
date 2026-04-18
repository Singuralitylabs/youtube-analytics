"""Channel-level endpoints (stats + subscriber/view timeline)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.collectors.sheets import HttpError as SheetsHttpError
from app.collectors.sheets import sheets_client
from app.collectors.youtube_data import HttpError as DataHttpError
from app.collectors.youtube_data import youtube_data_client
from app.schemas.responses import ChannelStats, TimeseriesPoint
from config.settings import get_settings

router = APIRouter(prefix="/api/channel", tags=["channel"])


_ALLOWED_METRICS = {"subscriber_count", "total_view_count"}


def _map_data_api_error(err: DataHttpError) -> HTTPException:
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


@router.get("/stats", response_model=ChannelStats)
def get_channel_stats() -> ChannelStats:
    """Return the most recent subscriber/view/video counts for the channel."""
    settings = get_settings()
    try:
        payload = youtube_data_client.get_channel_stats(settings.CHANNEL_ID)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except DataHttpError as err:
        raise _map_data_api_error(err) from err
    return ChannelStats(**payload)


@router.get("/timeseries", response_model=list[TimeseriesPoint])
def get_channel_timeseries(
    metric: str = Query(
        "subscriber_count",
        description="subscriber_count / total_view_count",
    ),
) -> list[TimeseriesPoint]:
    """Return the subscriber or total-view history stored in Google Sheets."""
    if metric not in _ALLOWED_METRICS:
        raise HTTPException(
            status_code=400,
            detail=(
                "metric は subscriber_count または total_view_count を指定してください"
            ),
        )

    try:
        rows = sheets_client.read_history()
    except SheetsHttpError as err:
        raise HTTPException(
            status_code=500,
            detail="Google Sheets API 障害が発生しました",
        ) from err

    return [
        TimeseriesPoint(collected_at=row["collected_at"], value=row[metric])
        for row in rows
    ]
