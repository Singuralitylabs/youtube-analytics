"""ISO-week helpers for the weekly report (Monday–Sunday, JST labels)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
_JST = ZoneInfo("Asia/Tokyo")


def previous_iso_week(today: date | None = None) -> tuple[str, date, date]:
    """Return (label, Mon, Sun) for the most recently completed ISO week (JST)."""
    if today is None:
        today = datetime.now(_JST).date()
    # ISO weekday: Mon=1 … Sun=7. Back up to the previous Sunday, then Mon.
    week_end = today - timedelta(days=today.isoweekday())
    week_start = week_end - timedelta(days=6)
    iso_year, iso_week, _ = week_start.isocalendar()
    label = f"{iso_year}-W{iso_week:02d}"
    return label, week_start, week_end


def parse_iso_week(label: str) -> tuple[date, date]:
    """Parse ``YYYY-Www`` into (Monday, Sunday)."""
    if not _WEEK_RE.match(label):
        raise ValueError(f"週ラベルの形式が不正です: {label}（YYYY-Www）")
    # %G = ISO year, %V = ISO week, %u = weekday (1=Mon)
    monday = datetime.strptime(f"{label}-1", "%G-W%V-%u").date()
    sunday = monday + timedelta(days=6)
    return monday, sunday


def is_week_label(label: str) -> bool:
    return bool(_WEEK_RE.match(label))
