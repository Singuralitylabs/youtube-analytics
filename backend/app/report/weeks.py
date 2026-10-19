"""ISO-week helpers for the weekly report (Monday–Sunday, JST labels).

YouTube Analytics ``startDate`` / ``endDate`` are interpreted in Pacific Time
(America/Los_Angeles). ``jst_range_to_analytics_dates`` maps a JST ISO week to
a fixed PT Mon–Sun calendar window (7 days, no overlap with the prior week).
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
_REPORT_RE = re.compile(r"^(\d{4}-W\d{2})\.md$")
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


def jst_range_to_analytics_dates(start_jst: date, end_jst: date) -> tuple[str, str]:
    """Map a JST ISO week (Mon–Sun) to Analytics API dates (PT calendar).

    Uses the **same calendar dates** as the JST week (exactly 7 days, Mon–Sun).
    Converting JST midnights to PT would expand the window to 8 days and make
    consecutive weeks share a boundary day (~14% double-count). The ~16–17h
    offset versus a true JST-aligned instant window is accepted and documented.
    """
    if end_jst < start_jst:
        raise ValueError("end_jst must be on or after start_jst")
    span = (end_jst - start_jst).days + 1
    if span != 7:
        raise ValueError(
            f"Analytics 期間は月〜日の7日である必要があります（got {span} days: "
            f"{start_jst}..{end_jst}）"
        )
    return start_jst.isoformat(), end_jst.isoformat()


def published_instant_to_jst_date(value: str) -> date | None:
    """Return the JST calendar date of a video publish timestamp.

    Accepts full ISO-8601 (``...Z`` or offset) or a bare ``YYYY-MM-DD``
    (treated as UTC midnight, then converted to JST).
    """
    if not value:
        return None
    text = value.strip()
    try:
        if "T" in text:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(_JST).date()
        # Date-only: interpret as UTC midnight, then convert to JST.
        day = date.fromisoformat(text[:10])
        dt = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        return dt.astimezone(_JST).date()
    except ValueError:
        return None


def published_at_jst_display(
    published_at_iso: str = "", published_at: str = ""
) -> str:
    """YYYY-MM-DD in JST for table display (falls back to the UTC date stem)."""
    raw = published_at_iso or published_at
    day = published_instant_to_jst_date(str(raw))
    if day is not None:
        return day.isoformat()
    return (published_at or raw or "")[:10]


def load_prior_weekly_report(output_dir: str, current_week: str) -> str | None:
    """Return text of the latest weekly report strictly before ``current_week``.

    Gaps from month-start skips are fine: pick the latest existing ``YYYY-Www.md``
    whose label sorts before ``current_week``.
    """
    if not os.path.isdir(output_dir):
        return None
    candidates: list[str] = []
    for name in os.listdir(output_dir):
        m = _REPORT_RE.match(name)
        if m and m.group(1) < current_week:
            candidates.append(m.group(1))
    if not candidates:
        return None
    latest = max(candidates)
    with open(os.path.join(output_dir, f"{latest}.md"), encoding="utf-8") as fp:
        return fp.read()


def should_skip_scheduled_weekly(
    *, event_name: str, utc_day_of_month: int
) -> bool:
    """True when a schedule run falls on UTC day 1 (monthly report day)."""
    return event_name == "schedule" and utc_day_of_month == 1


def is_most_recent_completed_week(week_end: date, today: date | None = None) -> bool:
    """True when ``week_end`` is the Sunday of the latest completed JST ISO week."""
    if today is None:
        today = datetime.now(_JST).date()
    latest_sunday = today - timedelta(days=today.isoweekday())
    return week_end == latest_sunday


# YouTube Analytics typically finalizes within 48–72 hours.
_ANALYTICS_FINALIZATION_LAG_DAYS = 3
# YouTube Analytics API trailing window (same as monthly builder).
_ANALYTICS_MAX_LOOKBACK_DAYS = 90


def analytics_may_include_unfinalized(
    week_end: date, today: date | None = None
) -> bool:
    """True when ``week_end`` is recent enough that Analytics may still be soft."""
    if today is None:
        today = datetime.now(_JST).date()
    if week_end > today:
        return True
    return (today - week_end).days <= _ANALYTICS_FINALIZATION_LAG_DAYS


def validate_report_week(
    week_start: date,
    week_end: date,
    *,
    today: date | None = None,
) -> None:
    """Raise ``ValueError`` when ``--week`` is unfinished, future, or too old."""
    if today is None:
        today = datetime.now(_JST).date()
    if week_end >= today:
        raise ValueError(
            f"まだ終わっていない週、または未来の週は指定できません"
            f"（{week_start}〜{week_end}、今日={today}）"
        )
    age_days = (today - week_end).days
    if age_days > _ANALYTICS_MAX_LOOKBACK_DAYS:
        raise ValueError(
            f"Analytics 取得可能期間（直近{_ANALYTICS_MAX_LOOKBACK_DAYS}日）より古い週です"
            f"（週末日={week_end}、経過={age_days}日）"
        )
