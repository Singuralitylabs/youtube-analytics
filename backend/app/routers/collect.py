"""POST /api/collect — snapshot current stats to Google Sheets."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.collectors.sheets import HttpError as SheetsHttpError
from app.collectors.sheets import sheets_client
from app.collectors.youtube_data import HttpError as DataHttpError
from app.collectors.youtube_data import youtube_data_client
from app.schemas.responses import CollectResult
from config.settings import get_settings

router = APIRouter(prefix="/api", tags=["collect"])


@router.post("/collect", response_model=CollectResult)
def collect() -> CollectResult:
    """Fetch current subscriber/view counts and append a row to Sheets."""
    settings = get_settings()
    try:
        stats = youtube_data_client.get_channel_stats(settings.CHANNEL_ID)
    except LookupError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except DataHttpError as err:
        status = getattr(err, "status_code", None) or getattr(
            getattr(err, "resp", None), "status", 500
        )
        if status == 403:
            raise HTTPException(
                status_code=429,
                detail="YouTube API のクォータ上限に達しました",
            ) from err
        raise HTTPException(
            status_code=500,
            detail="YouTube API 障害が発生しました",
        ) from err

    subscriber = int(stats["subscriber_count"])
    total_views = int(stats["total_view_count"])
    now = datetime.now()

    try:
        timestamp = sheets_client.append_record(now, subscriber, total_views)
    except SheetsHttpError as err:
        raise HTTPException(
            status_code=500,
            detail="Google Sheets API 障害が発生しました",
        ) from err

    return CollectResult(
        status="ok",
        collected_at=timestamp,
        subscriber_count=subscriber,
        total_view_count=total_views,
    )
