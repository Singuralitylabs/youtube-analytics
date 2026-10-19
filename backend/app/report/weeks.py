"""ISO-week helpers for the weekly report (Monday–Sunday, JST labels).

YouTube Analytics ``startDate`` / ``endDate`` are interpreted in Pacific Time
(America/Los_Angeles). Use ``jst_range_to_analytics_dates`` when querying the
API for a JST-labeled week so the request window covers that JST range.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

_WEEK_RE = re.compile(r"^(\d{4})-W(\d{2})$")
_REPORT_RE = re.compile(r"^(\d{4}-W\d{2})\.md$")
_JST = ZoneInfo("Asia/Tokyo")
# YouTube Analytics API calendar dates are Pacific Time.
_PT = ZoneInfo("America/Los_Angeles")


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
    """Map an inclusive JST calendar range to Analytics API dates (PT).

    Covers ``[start_jst 00:00 JST, end_jst 23:59:59 JST]`` by converting those
    instants to America/Los_Angeles calendar dates. Day-granularity means the
    PT window can be slightly wider than the JST week at the edges.
    """
    start_instant = datetime.combine(start_jst, time.min, tzinfo=_JST)
    end_instant = datetime.combine(end_jst, time(23, 59, 59), tzinfo=_JST)
    start_pt = start_instant.astimezone(_PT).date()
    end_pt = end_instant.astimezone(_PT).date()
    return start_pt.isoformat(), end_pt.isoformat()


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
