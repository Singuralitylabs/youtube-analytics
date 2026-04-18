"""Google Sheets API client (shares OAuth token with YouTube Analytics)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.collectors.youtube_analytics import load_credentials
from config.settings import get_settings


SHEET_NAME = "登録者数履歴"
SHEET_RANGE = f"{SHEET_NAME}!A:C"
HEADER_VALUES = ("収集日時", "登録者数", "総再生数")


class SheetsClient:
    """Read/write helper for the subscriber-history spreadsheet."""

    def __init__(self) -> None:
        self._service: Any | None = None

    def _build(self) -> Any:
        if self._service is None:
            creds = load_credentials()
            self._service = build(
                "sheets",
                "v4",
                credentials=creds,
                cache_discovery=False,
            )
        return self._service

    def _values(self) -> Any:
        return self._build().spreadsheets().values()

    def read_history(self) -> list[dict[str, Any]]:
        """Return every data row as list of {collected_at, subscriber_count, total_view_count}."""
        settings = get_settings()
        resp = self._values().get(
            spreadsheetId=settings.SPREADSHEET_ID,
            range=SHEET_RANGE,
        ).execute()

        rows: list[list[str]] = resp.get("values") or []
        results: list[dict[str, Any]] = []
        for row in rows:
            if not row:
                continue
            # Skip header row detected by non-numeric second column.
            if len(row) >= 2 and not _looks_like_int(row[1]):
                continue
            collected_at = row[0] if len(row) > 0 else ""
            subscriber = _to_int(row[1]) if len(row) > 1 else 0
            total_views = _to_int(row[2]) if len(row) > 2 else 0
            results.append(
                {
                    "collected_at": collected_at,
                    "subscriber_count": subscriber,
                    "total_view_count": total_views,
                }
            )
        return results

    def append_record(
        self,
        collected_at: datetime,
        subscriber_count: int,
        total_view_count: int,
    ) -> str:
        """Append a new subscriber-history row and return its formatted timestamp."""
        settings = get_settings()
        timestamp = collected_at.strftime("%Y-%m-%d %H:%M:%S")
        self._values().append(
            spreadsheetId=settings.SPREADSHEET_ID,
            range=SHEET_RANGE,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={
                "values": [
                    [timestamp, subscriber_count, total_view_count]
                ]
            },
        ).execute()
        return timestamp


def _to_int(value: Any) -> int:
    """Best-effort int conversion that tolerates comma-formatted strings."""
    if isinstance(value, int):
        return value
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0


def _looks_like_int(value: Any) -> bool:
    try:
        int(str(value).replace(",", "").strip())
        return True
    except (ValueError, TypeError):
        return False


sheets_client = SheetsClient()

__all__ = ["SheetsClient", "sheets_client", "HttpError"]
