"""Collect and compute the deterministic data bundle for a monthly report.

This module is the *numeric* half of the hybrid report generator. It reuses the
collector singletons directly and produces a JSON-serialisable ``dict`` that:

* the renderer turns into the fixed tables (snapshot, rankings), and
* the author (Gemini API) reads to write the interpretive prose.

Design notes that mirror ``docs/analysis-playbook.md``:

* Retention uses the API's official ``averageViewPercentage``, obtained as an
  extra column of the ``top_videos`` multi-metric query. (Sorting *by* that
  metric with ``dimensions=video`` is unsupported and returns 400/500, so it
  rides along on a ``views``/``estimatedMinutesWatched`` sort instead.)
* Retention is length-dependent, so every entry carries ``duration_sec`` and the
  drilldown "bottom retention" set is restricted to well-exposed videos to avoid
  the n=1 / short-video pitfalls called out in the playbook anti-patterns.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from typing import Any

from google.auth.exceptions import GoogleAuthError

from app.collectors.sheets import HttpError as SheetsHttpError
from app.collectors.sheets import sheets_client
from app.collectors.youtube_analytics import HttpError as AnalyticsHttpError
from app.collectors.youtube_analytics import youtube_analytics_client
from app.collectors.youtube_data import HttpError as DataHttpError
from app.collectors.youtube_data import youtube_data_client
from config.settings import get_settings

# OAuth-backed calls (Analytics, Sheets) can fail on HTTP errors *or* on
# credential problems raised by load_credentials (expired/revoked token, missing
# token file). Treat all of these as "this section is unavailable" rather than
# letting a dead token abort the whole report.
_OAUTH_ERRORS = (AnalyticsHttpError, GoogleAuthError, FileNotFoundError)

# How many videos to pull per ranking call (covers Top10 tables + split matrix).
_RANKING_LIMIT = 50
# Videos considered "well exposed" enough to trust their retention figure.
_EXPOSURE_POOL = 20
# Default trailing analysis window (YouTube Analytics API maximum).
_WINDOW_DAYS = 90


def _log(message: str) -> None:
    """Emit progress/diagnostics to stderr so stdout stays machine-parseable."""
    print(f"[builder] {message}", file=sys.stderr)


def _pct(numerator: float, denominator: float) -> float | None:
    """Return numerator/denominator as a percentage, or None when undefined."""
    if not denominator:
        return None
    return round(numerator / denominator * 100, 2)


def build_data_bundle(
    *,
    days: int = _WINDOW_DAYS,
    drilldown_count: int = 6,
    month: str | None = None,
) -> dict[str, Any]:
    """Gather every number the report needs into one structured dict.

    Args:
        days: trailing window for the YouTube Analytics API (max 90).
        drilldown_count: max number of videos to deep-dive.
        month: report label ``YYYY-MM`` (defaults to the current month).

    Returns:
        A JSON-serialisable bundle. Network failures degrade gracefully: a
        failed section becomes an empty list / null rather than aborting.
    """
    settings = get_settings()
    channel_id = settings.CHANNEL_ID
    today = date.today()
    window_start = (today - timedelta(days=days - 1)).isoformat()
    window_end = today.isoformat()
    label = month or today.strftime("%Y-%m")

    bundle: dict[str, Any] = {
        "meta": {
            "month": label,
            "channel_id": channel_id,
            "channel_title": "",
            "window_start": window_start,
            "window_end": window_end,
            "window_days": days,
            "generated_at": today.isoformat(),
        },
        "snapshot": {},
        "subscriber_history": [],
        "rankings": {"views": [], "minutes": [], "retention": []},
        "split_rank": {
            "high_views_high_retention": [],
            "high_views_low_retention": [],
            "low_views_high_retention": [],
            "low_views_low_retention": [],
        },
        "engagement_ranking": [],
        "drilldowns": [],
        "warnings": [],
    }

    # ---- Channel snapshot + title -------------------------------------------
    try:
        bundle["meta"]["channel_title"] = youtube_data_client.get_channel_title(
            channel_id
        )
    except (DataHttpError, LookupError) as err:
        bundle["warnings"].append(f"channel title 取得失敗: {err}")

    try:
        stats = youtube_data_client.get_channel_stats(channel_id)
    except (DataHttpError, LookupError) as err:
        bundle["warnings"].append(f"channel stats 取得失敗: {err}")
        stats = {}
    bundle["snapshot"] = _build_snapshot(stats)

    # ---- Subscriber history (Sheets) + month-over-month delta ---------------
    history = _safe_read_history(bundle)
    bundle["subscriber_history"] = history
    _apply_mom_delta(bundle["snapshot"], history, today)

    # ---- All videos (titles, duration, engagement) --------------------------
    videos_meta = _build_videos_meta(channel_id, bundle)
    bundle["snapshot"]["avg_views_per_video"] = _avg_views_per_video(
        bundle["snapshot"], videos_meta
    )

    # ---- Rankings -----------------------------------------------------------
    # One multi-metric "top videos" query per sort key. This returns the real
    # averageViewPercentage per video (sorting BY that metric is unsupported).
    views_rows = _safe_top_videos(days, "-views", bundle)
    minutes_rows = _safe_top_videos(days, "-estimatedMinutesWatched", bundle)

    retention_by_id = _retention_map(views_rows, minutes_rows)
    retention_rows = _retention_ranking(
        retention_by_id, views_rows, minutes_rows, videos_meta
    )

    bundle["rankings"]["views"] = _hydrate_ranking(
        views_rows, videos_meta, retention_by_id, value_key="views"
    )
    bundle["rankings"]["minutes"] = _hydrate_ranking(
        minutes_rows, videos_meta, retention_by_id, value_key="minutes"
    )
    bundle["rankings"]["retention"] = retention_rows

    # ---- Split-rank matrix --------------------------------------------------
    bundle["split_rank"] = _build_split_rank(
        views_rows, retention_rows, videos_meta
    )

    # ---- Engagement (Pattern C) --------------------------------------------
    bundle["engagement_ranking"] = _engagement_ranking(views_rows, videos_meta)

    # ---- Drilldown candidates + per-video detail ----------------------------
    candidates = _select_drilldowns(
        views_rows, retention_rows, drilldown_count
    )
    bundle["drilldowns"] = [
        _build_drilldown(vid, days, videos_meta, retention_rows, bundle)
        for vid in candidates
    ]

    return bundle


# --------------------------------------------------------------------------- #
# Snapshot helpers
# --------------------------------------------------------------------------- #
def _build_snapshot(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "subscriber_count": int(stats.get("subscriber_count", 0)),
        "total_view_count": int(stats.get("total_view_count", 0)),
        "video_count": int(stats.get("video_count", 0)),
        "avg_views_per_video": None,
        "subscriber_delta": None,
        "subscriber_delta_pct": None,
        "total_view_delta": None,
        "total_view_delta_pct": None,
        "delta_baseline_date": None,
    }


def _avg_views_per_video(
    snapshot: dict[str, Any], videos_meta: dict[str, Any]
) -> int | None:
    total = snapshot.get("total_view_count") or 0
    count = snapshot.get("video_count") or len(videos_meta)
    if not count:
        return None
    return round(total / count)


def _safe_read_history(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        return sheets_client.read_history()
    except (SheetsHttpError, FileNotFoundError) as err:
        bundle["warnings"].append(f"Sheets 履歴の読み取り失敗: {err}")
        return []
    except Exception as err:  # noqa: BLE001 - history is optional; never abort.
        bundle["warnings"].append(f"Sheets 履歴の読み取り失敗: {err}")
        return []


def _parse_collected_at(value: str) -> date | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _apply_mom_delta(
    snapshot: dict[str, Any],
    history: list[dict[str, Any]],
    today: date,
) -> None:
    """Fill in month-over-month deltas using the Sheets snapshot closest to ~30d ago."""
    dated = [
        (_parse_collected_at(rec.get("collected_at", "")), rec)
        for rec in history
    ]
    dated = [(d, rec) for d, rec in dated if d is not None]
    if len(dated) < 1:
        return

    target = today - timedelta(days=30)
    # Prefer the record nearest to 30 days ago; require a non-trivial gap.
    baseline = min(dated, key=lambda item: abs((item[0] - target).days))
    base_date, base_rec = baseline
    if (today - base_date).days < 7:
        return  # Too recent to be a meaningful "previous month" baseline.

    sub_now = snapshot["subscriber_count"]
    view_now = snapshot["total_view_count"]
    sub_base = int(base_rec.get("subscriber_count", 0))
    view_base = int(base_rec.get("total_view_count", 0))

    snapshot["delta_baseline_date"] = base_date.isoformat()
    if sub_base:
        snapshot["subscriber_delta"] = sub_now - sub_base
        snapshot["subscriber_delta_pct"] = _pct(sub_now - sub_base, sub_base)
    if view_base:
        snapshot["total_view_delta"] = view_now - view_base
        snapshot["total_view_delta_pct"] = _pct(view_now - view_base, view_base)


# --------------------------------------------------------------------------- #
# Video metadata + rankings
# --------------------------------------------------------------------------- #
def _build_videos_meta(
    channel_id: str, bundle: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    try:
        video_ids = youtube_data_client.list_video_ids(channel_id)
        videos = youtube_data_client.get_videos(video_ids)
    except (DataHttpError, LookupError) as err:
        bundle["warnings"].append(f"動画一覧の取得失敗: {err}")
        return {}

    meta: dict[str, dict[str, Any]] = {}
    for v in videos:
        engagement = _pct(
            v.get("like_count", 0) + v.get("comment_count", 0),
            v.get("view_count", 0),
        )
        meta[v["video_id"]] = {**v, "engagement_pct": engagement}
    _log(f"動画メタ {len(meta)} 件")
    return meta


def _safe_top_videos(
    days: int, sort: str, bundle: dict[str, Any]
) -> list[dict[str, Any]]:
    try:
        return youtube_analytics_client.top_videos(days, _RANKING_LIMIT, sort)
    except _OAUTH_ERRORS as err:
        bundle["warnings"].append(f"top_videos(sort={sort}) 取得失敗: {err}")
        return []


def _retention_map(*row_lists: list[dict[str, Any]]) -> dict[str, float]:
    """video_id -> averageViewPercentage, unioned across the supplied rankings."""
    out: dict[str, float] = {}
    for rows in row_lists:
        for r in rows:
            vid = r.get("video_id")
            if vid and vid not in out and r.get("retention_pct") is not None:
                out[vid] = r["retention_pct"]
    return out


def _retention_ranking(
    retention_by_id: dict[str, float],
    views_rows: list[dict[str, Any]],
    minutes_rows: list[dict[str, Any]],
    videos_meta: dict[str, Any],
) -> list[dict[str, Any]]:
    """Per-video retention list (desc), enriched with views/length context."""
    avg_sec: dict[str, Any] = {}
    views_by_id: dict[str, int] = {}
    for rows in (views_rows, minutes_rows):
        for r in rows:
            avg_sec.setdefault(r["video_id"], r.get("avg_view_sec"))
            views_by_id.setdefault(r["video_id"], r.get("views", 0))

    rows: list[dict[str, Any]] = []
    for vid, retention in retention_by_id.items():
        info = videos_meta.get(vid, {})
        rows.append(
            {
                "video_id": vid,
                "title": info.get("title", ""),
                "published_at": info.get("published_at", ""),
                "retention_pct": retention,
                "avg_view_sec": avg_sec.get(vid),
                "duration_sec": info.get("duration_sec", 0),
                "views": views_by_id.get(vid, info.get("view_count", 0)),
            }
        )
    rows.sort(key=lambda x: x["retention_pct"], reverse=True)
    return rows


def _hydrate_ranking(
    rows: list[dict[str, Any]],
    videos_meta: dict[str, Any],
    retention_by_id: dict[str, float],
    *,
    value_key: str,
) -> list[dict[str, Any]]:
    """Attach title/retention/engagement to a metric ranking, ranked from 1."""
    result: list[dict[str, Any]] = []
    for idx, r in enumerate(rows, start=1):
        vid = r["video_id"]
        info = videos_meta.get(vid, {})
        result.append(
            {
                "rank": idx,
                "video_id": vid,
                "title": info.get("title", ""),
                "published_at": info.get("published_at", ""),
                value_key: round(r.get(value_key, 0)),
                "retention_pct": r.get("retention_pct", retention_by_id.get(vid)),
                "engagement_pct": info.get("engagement_pct"),
                "duration_sec": info.get("duration_sec", 0),
            }
        )
    return result


def _build_split_rank(
    views_rows: list[dict[str, Any]],
    retention_rows: list[dict[str, Any]],
    videos_meta: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Cross views-rank vs retention-rank into the playbook's 4 quadrants."""
    views_order = [r["video_id"] for r in views_rows]
    retention_order = [r["video_id"] for r in retention_rows]
    common = [v for v in views_order if v in set(retention_order)]
    if not common:
        return {
            "high_views_high_retention": [],
            "high_views_low_retention": [],
            "low_views_high_retention": [],
            "low_views_low_retention": [],
        }

    views_rank = {v: i for i, v in enumerate(views_order)}
    retention_rank = {v: i for i, v in enumerate(retention_order)}
    n = len(common)
    third = max(1, n // 3)

    def _bucket(vid: str) -> tuple[str, str]:
        v_high = views_rank[vid] < third
        v_low = views_rank[vid] >= n - third
        r_high = retention_rank[vid] < third
        r_low = retention_rank[vid] >= n - third
        return (
            "high" if v_high else "low" if v_low else "mid",
            "high" if r_high else "low" if r_low else "mid",
        )

    quadrants: dict[str, list[dict[str, Any]]] = {
        "high_views_high_retention": [],
        "high_views_low_retention": [],
        "low_views_high_retention": [],
        "low_views_low_retention": [],
    }
    mapping = {
        ("high", "high"): "high_views_high_retention",
        ("high", "low"): "high_views_low_retention",
        ("low", "high"): "low_views_high_retention",
        ("low", "low"): "low_views_low_retention",
    }
    retention_by_id = {r["video_id"]: r["retention_pct"] for r in retention_rows}
    # Show the 90-day window views (consistent with the ranking tables and the
    # quadrant classification), NOT the lifetime view_count from the Data API.
    views90_by_id = {r["video_id"]: r["views"] for r in views_rows}
    for vid in common:
        key = mapping.get(_bucket(vid))
        if not key or len(quadrants[key]) >= 4:
            continue
        info = videos_meta.get(vid, {})
        quadrants[key].append(
            {
                "video_id": vid,
                "title": info.get("title", ""),
                "views": views90_by_id.get(vid, 0),
                "retention_pct": retention_by_id.get(vid),
                "duration_sec": info.get("duration_sec", 0),
            }
        )
    return quadrants


def _engagement_ranking(
    views_rows: list[dict[str, Any]], videos_meta: dict[str, Any]
) -> list[dict[str, Any]]:
    """Top videos by (likes+comments)/views among videos with real exposure."""
    exposure = {r["video_id"] for r in views_rows}
    rows = [
        {
            "video_id": vid,
            "title": info.get("title", ""),
            "published_at": info.get("published_at", ""),
            "engagement_pct": info.get("engagement_pct"),
            "views": info.get("view_count", 0),
        }
        for vid, info in videos_meta.items()
        if vid in exposure and info.get("engagement_pct") is not None
    ]
    rows.sort(key=lambda x: x["engagement_pct"], reverse=True)
    return rows[:10]


def _select_drilldowns(
    views_rows: list[dict[str, Any]],
    retention_rows: list[dict[str, Any]],
    limit: int,
) -> list[str]:
    """Deterministically pick videos to deep-dive (top views, bottom retention, hidden gems)."""
    views_order = [r["video_id"] for r in views_rows]
    exposure = set(views_order[:_EXPOSURE_POOL])
    top_views = views_order[:2]

    # Bottom retention, but only among well-exposed videos (avoid n=1 noise).
    bottom_retention = [
        r["video_id"]
        for r in sorted(retention_rows, key=lambda x: x["retention_pct"])
        if r["video_id"] in exposure
    ][:2]

    # Hidden gems: high retention but NOT among the most-viewed.
    not_top_views = set(views_order[:15])
    hidden_gems = [
        r["video_id"] for r in retention_rows if r["video_id"] not in not_top_views
    ][:2]

    ordered: list[str] = []
    for vid in [*top_views, *bottom_retention, *hidden_gems]:
        if vid and vid not in ordered:
            ordered.append(vid)
    return ordered[:limit]


def _build_drilldown(
    video_id: str,
    days: int,
    videos_meta: dict[str, Any],
    retention_rows: list[dict[str, Any]],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    info = videos_meta.get(video_id, {})
    retention_by_id = {r["video_id"]: r["retention_pct"] for r in retention_rows}

    detail: dict[str, Any] = {
        "video_id": video_id,
        "title": info.get("title", ""),
        "published_at": info.get("published_at", ""),
        "duration_sec": info.get("duration_sec", 0),
        "view_count": info.get("view_count", 0),
        "like_count": info.get("like_count", 0),
        "comment_count": info.get("comment_count", 0),
        "engagement_pct": info.get("engagement_pct"),
        "retention_pct": retention_by_id.get(video_id),
        "traffic": [],
        "demographics": [],
        "timeseries_views": [],
        "timeseries_retention": [],
    }

    try:
        traffic = youtube_analytics_client.traffic_sources(video_id, days)
        total = sum(t["views"] for t in traffic) or 1
        detail["traffic"] = [
            {**t, "share_pct": round(t["views"] / total * 100, 1)}
            for t in traffic
        ]
    except _OAUTH_ERRORS as err:
        bundle["warnings"].append(f"traffic({video_id}) 取得失敗: {err}")

    try:
        detail["demographics"] = youtube_analytics_client.demographics(
            video_id, days
        )
    except _OAUTH_ERRORS as err:
        bundle["warnings"].append(f"demographics({video_id}) 取得失敗: {err}")

    try:
        detail["timeseries_views"] = youtube_analytics_client.video_timeseries(
            video_id, "views", days
        )
    except _OAUTH_ERRORS as err:
        bundle["warnings"].append(f"timeseries views({video_id}) 取得失敗: {err}")

    try:
        detail["timeseries_retention"] = (
            youtube_analytics_client.video_timeseries(
                video_id, "averageViewPercentage", days
            )
        )
    except _OAUTH_ERRORS as err:
        bundle["warnings"].append(
            f"timeseries retention({video_id}) 取得失敗: {err}"
        )

    return detail
