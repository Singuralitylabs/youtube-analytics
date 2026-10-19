"""Unit tests for weekly helpers, retry, builder pure logic (no external APIs)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.collectors.youtube_analytics import YouTubeAnalyticsClient  # noqa: E402
from app.report import builder, renderer, slack  # noqa: E402
from app.report.retry import (  # noqa: E402
    is_retryable_api_error,
    is_retryable_gemini_error,
    with_retry,
)
from app.report.weeks import (  # noqa: E402
    analytics_may_include_unfinalized,
    is_most_recent_completed_week,
    jst_range_to_analytics_dates,
    load_prior_weekly_report,
    parse_iso_week,
    previous_iso_week,
    published_at_jst_display,
    published_instant_to_jst_date,
    should_skip_scheduled_weekly,
    validate_report_week,
)


class WeekHelpersTest(unittest.TestCase):
    def test_parse_iso_week(self) -> None:
        start, end = parse_iso_week("2026-W41")
        self.assertEqual(start, date(2026, 10, 5))
        self.assertEqual(end, date(2026, 10, 11))
        self.assertEqual(start.isoweekday(), 1)
        self.assertEqual(end.isoweekday(), 7)

    def test_previous_iso_week_on_monday(self) -> None:
        # Monday 2026-10-19 → previous week is W42 (2026-10-12..18)
        label, start, end = previous_iso_week(date(2026, 10, 19))
        self.assertEqual(label, "2026-W42")
        self.assertEqual(start, date(2026, 10, 12))
        self.assertEqual(end, date(2026, 10, 18))

    def test_jst_range_to_analytics_dates_is_seven_days(self) -> None:
        # Same calendar dates (PT Mon–Sun), not JST-midnight→PT (which was 8 days).
        start, end = jst_range_to_analytics_dates(date(2026, 10, 5), date(2026, 10, 11))
        self.assertEqual(start, "2026-10-05")
        self.assertEqual(end, "2026-10-11")
        self.assertEqual(
            (date.fromisoformat(end) - date.fromisoformat(start)).days + 1, 7
        )

    def test_jst_range_consecutive_weeks_do_not_overlap(self) -> None:
        a0, a1 = jst_range_to_analytics_dates(date(2026, 10, 5), date(2026, 10, 11))
        b0, b1 = jst_range_to_analytics_dates(date(2026, 10, 12), date(2026, 10, 18))
        self.assertEqual(a1, "2026-10-11")
        self.assertEqual(b0, "2026-10-12")
        self.assertNotEqual(a1, b0)

    def test_published_instant_jst_crosses_utc_midnight(self) -> None:
        # 2026-10-04T16:00:00Z = 2026-10-05 01:00 JST → belongs to W41 Mon
        self.assertEqual(
            published_instant_to_jst_date("2026-10-04T16:00:00Z"),
            date(2026, 10, 5),
        )
        # UTC date cut would wrongly say Oct 4
        self.assertNotEqual(
            published_instant_to_jst_date("2026-10-04T16:00:00Z"),
            date(2026, 10, 4),
        )

    def test_published_at_jst_display(self) -> None:
        self.assertEqual(
            published_at_jst_display("2026-10-04T16:00:00Z", "2026-10-04"),
            "2026-10-05",
        )

    def test_should_skip_scheduled_weekly(self) -> None:
        self.assertTrue(
            should_skip_scheduled_weekly(event_name="schedule", utc_day_of_month=1)
        )
        self.assertFalse(
            should_skip_scheduled_weekly(event_name="schedule", utc_day_of_month=2)
        )
        self.assertFalse(
            should_skip_scheduled_weekly(
                event_name="workflow_dispatch", utc_day_of_month=1
            )
        )

    def test_load_prior_weekly_report_skips_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "2026-W39.md").write_text("W39", encoding="utf-8")
            # W40 missing (month-start skip); current is W41
            Path(tmp, "2026-W41.md").write_text("W41", encoding="utf-8")
            prior = load_prior_weekly_report(tmp, "2026-W41")
            self.assertEqual(prior, "W39")

    def test_load_prior_crosses_year_w53_to_w01(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "2026-W53.md").write_text("W53", encoding="utf-8")
            prior = load_prior_weekly_report(tmp, "2027-W01")
            self.assertEqual(prior, "W53")
        # Lexicographic week labels still order across the year boundary.
        self.assertLess("2026-W53", "2027-W01")

    def test_is_most_recent_completed_week(self) -> None:
        # Monday 2026-10-19 → latest completed Sunday is 2026-10-18
        self.assertTrue(
            is_most_recent_completed_week(date(2026, 10, 18), date(2026, 10, 19))
        )
        self.assertFalse(
            is_most_recent_completed_week(date(2026, 7, 12), date(2026, 10, 19))
        )

    def test_analytics_may_include_unfinalized_only_when_recent(self) -> None:
        self.assertTrue(
            analytics_may_include_unfinalized(date(2026, 10, 18), date(2026, 10, 21))
        )
        self.assertFalse(
            analytics_may_include_unfinalized(date(2026, 7, 12), date(2026, 10, 19))
        )

    def test_validate_report_week_rejects_future_and_too_old(self) -> None:
        today = date(2026, 10, 19)
        with self.assertRaises(ValueError):
            validate_report_week(date(2026, 10, 19), date(2026, 10, 25), today=today)
        with self.assertRaises(ValueError):
            validate_report_week(date(2026, 6, 1), date(2026, 6, 7), today=today)
        # Just-completed previous week is OK.
        validate_report_week(date(2026, 10, 12), date(2026, 10, 18), today=today)


class RetryTest(unittest.TestCase):
    def test_retryable_gemini_503(self) -> None:
        class FakeErr(Exception):
            status_code = 503

        self.assertTrue(is_retryable_gemini_error(FakeErr("unavailable")))

    def test_non_retryable_gemini_401(self) -> None:
        class FakeErr(Exception):
            status_code = 401

        self.assertFalse(is_retryable_gemini_error(FakeErr("auth")))

    def test_false_positive_5000_not_retryable(self) -> None:
        self.assertFalse(
            is_retryable_gemini_error(Exception("Invalid value 5000 for field"))
        )

    def test_ambiguous_try_again_not_retryable(self) -> None:
        self.assertFalse(
            is_retryable_gemini_error(Exception("Please try again with a valid key"))
        )

    def test_status_in_message_with_boundary(self) -> None:
        self.assertTrue(
            is_retryable_gemini_error(Exception("503 UNAVAILABLE. high demand"))
        )

    def test_with_retry_recovers_after_503(self) -> None:
        calls = {"n": 0}

        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise Exception("503 UNAVAILABLE high demand")
            return "ok"

        with patch("app.report.retry.time.sleep", return_value=None):
            result = with_retry(
                flaky,
                max_attempts=4,
                base_delay_s=0.01,
                factor=2.0,
                label="test",
                is_retryable=is_retryable_gemini_error,
            )
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)

    def test_api_retryable_connection(self) -> None:
        self.assertTrue(is_retryable_api_error(ConnectionError("reset")))

    def test_httpx_transport_errors_are_retryable_for_gemini(self) -> None:
        import httpx

        self.assertTrue(is_retryable_gemini_error(httpx.ConnectError("boom")))
        self.assertTrue(is_retryable_gemini_error(httpx.ReadTimeout("slow")))
        self.assertTrue(
            is_retryable_gemini_error(httpx.RemoteProtocolError("disconnect"))
        )
        self.assertTrue(is_retryable_api_error(httpx.ConnectError("boom")))


class BuilderWeeklyLogicTest(unittest.TestCase):
    def test_period_with_wow_omits_pct_when_baseline_small(self) -> None:
        period = builder._period_with_wow(
            {"views": 40, "minutes": 10, "retention_pct": 30.0},
            {"views": 20, "minutes": 5, "retention_pct": 28.0},
        )
        self.assertEqual(period["views_delta"], 20)
        self.assertIsNone(period["views_delta_pct"])  # prior views < 50
        self.assertEqual(period["retention_delta_pp"], 2.0)

    def test_hydrate_weekly_ranking_rank_delta_and_new(self) -> None:
        rows = [
            {"video_id": "a", "views": 100, "retention_pct": 40.0},
            {"video_id": "b", "views": 80, "retention_pct": 30.0},
            {"video_id": "c", "views": 70, "retention_pct": 20.0},
        ]
        meta = {
            "a": {
                "title": "A",
                "published_at": "2026-01-01",
                "published_at_iso": "2026-01-01T00:00:00Z",
                "engagement_pct": 1.0,
            },
            "b": {
                "title": "B",
                "published_at": "2026-10-06",
                "published_at_iso": "2026-10-06T03:00:00Z",  # in-week → NEW
                "engagement_pct": 2.0,
            },
            "c": {
                "title": "C",
                "published_at": "2026-01-02",
                "published_at_iso": "2026-01-02T00:00:00Z",  # old, not in prior → 圏外
                "engagement_pct": 1.5,
            },
        }
        out = builder._hydrate_weekly_ranking(
            rows,
            meta,
            {},
            prior_rank_by_id={"a": 3},
            value_key="views",
            top_n=5,
            week_start=date(2026, 10, 5),
            week_end=date(2026, 10, 11),
            prior_available=True,
        )
        self.assertEqual(out[0]["prior_status"], "ranked")
        self.assertEqual(out[0]["rank_delta"], 2)
        self.assertEqual(out[1]["prior_status"], "new")
        self.assertEqual(out[2]["prior_status"], "out")
        self.assertEqual(renderer._rank_change(out[1]), "NEW")
        self.assertEqual(renderer._rank_change(out[2]), "圏外")
        unavailable = builder._hydrate_weekly_ranking(
            rows[:1],
            meta,
            {},
            prior_rank_by_id={},
            value_key="views",
            top_n=5,
            week_start=date(2026, 10, 5),
            week_end=date(2026, 10, 11),
            prior_available=False,
        )
        self.assertEqual(unavailable[0]["prior_status"], "unavailable")
        self.assertEqual(renderer._rank_change(unavailable[0]), "—")

    def test_new_videos_in_week_uses_jst_instant(self) -> None:
        week_start, week_end = date(2026, 10, 5), date(2026, 10, 11)
        meta = {
            "in": {
                "title": "In week",
                "published_at": "2026-10-04",
                "published_at_iso": "2026-10-04T16:00:00Z",  # JST Oct 5
                "duration_sec": 60,
                "engagement_pct": 1.0,
            },
            "out": {
                "title": "Out",
                "published_at": "2026-10-04",
                "published_at_iso": "2026-10-04T10:00:00Z",  # JST Oct 4 19:00
                "duration_sec": 60,
                "engagement_pct": 1.0,
            },
        }
        views = [{"video_id": "in", "views": 10, "minutes": 1, "retention_pct": 50.0}]
        bundle: dict = {"warnings": []}
        rows = builder._new_videos_in_week(
            meta,
            week_start,
            week_end,
            views,
            {},
            api_start="2026-10-04",
            api_end="2026-10-11",
            bundle=bundle,
        )
        self.assertEqual([r["video_id"] for r in rows], ["in"])
        # Display date is JST (Oct 5), not UTC stem (Oct 4).
        self.assertEqual(rows[0]["published_at"], "2026-10-05")

    def test_new_videos_fetches_metrics_outside_top_videos(self) -> None:
        """New videos missing from top_videos still get real period metrics."""
        week_start, week_end = date(2026, 10, 5), date(2026, 10, 11)
        meta = {
            "low": {
                "title": "Outside Top50",
                "published_at": "2026-10-06",
                "published_at_iso": "2026-10-06T03:00:00Z",
                "duration_sec": 60,
                "engagement_pct": 1.0,
            }
        }
        bundle: dict = {"warnings": []}
        fetched = [
            {
                "video_id": "low",
                "views": 42,
                "minutes": 7,
                "retention_pct": 55.0,
            }
        ]
        with patch(
            "app.report.builder._safe_video_period_metrics",
            return_value=fetched,
        ) as mock_fetch:
            rows = builder._new_videos_in_week(
                meta,
                week_start,
                week_end,
                views_rows=[],  # not in top_videos
                retention_by_id={},
                api_start="2026-10-04",
                api_end="2026-10-11",
                bundle=bundle,
            )
        mock_fetch.assert_called_once_with(
            ["low"], "2026-10-04", "2026-10-11", bundle
        )
        self.assertEqual(rows[0]["views"], 42)
        self.assertEqual(rows[0]["retention_pct"], 55.0)
        self.assertEqual(rows[0]["published_at"], "2026-10-06")

    def test_hydrate_weekly_ranking_published_at_jst(self) -> None:
        rows = [{"video_id": "a", "views": 10, "retention_pct": 40.0}]
        meta = {
            "a": {
                "title": "A",
                "published_at": "2026-10-04",
                "published_at_iso": "2026-10-04T16:00:00Z",
                "engagement_pct": 1.0,
            }
        }
        out = builder._hydrate_weekly_ranking(
            rows, meta, {}, prior_rank_by_id={}, value_key="views", top_n=5
        )
        self.assertEqual(out[0]["published_at"], "2026-10-05")

    def test_safe_top_videos_connection_error_degrades(self) -> None:
        bundle: dict = {"warnings": []}

        def boom(*_args: object, **_kwargs: object) -> list:
            raise ConnectionError("reset by peer")

        with patch("app.report.builder._call_api", side_effect=boom):
            rows = builder._safe_top_videos(7, "-views", bundle)
        self.assertEqual(rows, [])
        self.assertTrue(any("reset by peer" in w for w in bundle["warnings"]))

    def test_safe_channel_totals_connection_error_degrades(self) -> None:
        bundle: dict = {"warnings": []}

        def boom(*_args: object, **_kwargs: object) -> dict:
            raise ConnectionError("timeout")

        with patch("app.report.builder._call_api", side_effect=boom):
            totals = builder._safe_channel_totals("2026-10-04", "2026-10-11", bundle)
        self.assertEqual(totals["views"], 0)
        self.assertIsNone(totals["retention_pct"])
        self.assertTrue(bundle["warnings"])

    def test_build_weekly_bundle_wow_and_analytics_meta(self) -> None:
        week_start, week_end = date(2026, 10, 5), date(2026, 10, 11)

        def fake_top(
            days: int,
            limit: int,
            sort: str,
            *,
            start_date: str | None = None,
            end_date: str | None = None,
        ) -> list:
            if start_date == "2026-10-05":  # current week PT calendar (= JST dates)
                if "views" in sort:
                    return [
                        {
                            "video_id": "v1",
                            "views": 200,
                            "minutes": 50,
                            "retention_pct": 40.0,
                        },
                        {
                            "video_id": "v2",
                            "views": 100,
                            "minutes": 80,
                            "retention_pct": 30.0,
                        },
                    ]
                return [
                    {
                        "video_id": "v2",
                        "views": 100,
                        "minutes": 80,
                        "retention_pct": 30.0,
                    },
                    {
                        "video_id": "v1",
                        "views": 200,
                        "minutes": 50,
                        "retention_pct": 40.0,
                    },
                ]
            # prior week
            if "views" in sort:
                return [
                    {
                        "video_id": "v2",
                        "views": 90,
                        "minutes": 70,
                        "retention_pct": 28.0,
                    },
                    {
                        "video_id": "v1",
                        "views": 80,
                        "minutes": 40,
                        "retention_pct": 35.0,
                    },
                ]
            return []

        fake_client = MagicMock()
        fake_client.top_videos.side_effect = fake_top
        fake_client.channel_totals.side_effect = [
            {"views": 300, "minutes": 100, "retention_pct": 35.0},
            {"views": 200, "minutes": 80, "retention_pct": 32.0},
        ]
        fake_client.video_period_metrics.return_value = []

        videos_meta = {
            "v1": {
                "title": "One",
                "published_at": "2026-09-01",
                "published_at_iso": "2026-09-01T00:00:00Z",
                "duration_sec": 60,
                "engagement_pct": 1.5,
                "view_count": 1000,
            },
            "v2": {
                "title": "Two",
                "published_at": "2026-10-06",
                "published_at_iso": "2026-10-06T03:00:00Z",
                "duration_sec": 90,
                "engagement_pct": 2.0,
                "view_count": 500,
            },
        }

        with (
            patch("app.report.builder.get_settings") as gs,
            patch("app.report.builder.youtube_data_client") as data,
            patch("app.report.builder.youtube_analytics_client", fake_client),
            patch("app.report.builder._safe_read_history", return_value=[]),
            patch("app.report.builder._build_videos_meta", return_value=videos_meta),
        ):
            gs.return_value.CHANNEL_ID = "UCtest"
            data.get_channel_title.return_value = "Test"
            data.get_channel_stats.return_value = {
                "subscriber_count": 100,
                "total_view_count": 1000,
                "video_count": 2,
            }
            # _call_api just invokes fn
            with patch(
                "app.report.builder._call_api",
                side_effect=lambda label, fn: fn(),
            ):
                bundle = builder.build_weekly_bundle(
                    week_start, week_end, week_label="2026-W41"
                )

        self.assertEqual(bundle["meta"]["analytics_start"], "2026-10-05")
        self.assertEqual(bundle["meta"]["analytics_end"], "2026-10-11")
        # Flag depends on run date vs week_end; historical regenerations stay False.
        self.assertIn("analytics_may_include_unfinalized", bundle["meta"])
        self.assertEqual(bundle["period"]["views"], 300)
        self.assertEqual(bundle["period"]["views_delta"], 100)
        views_rank = bundle["rankings"]["views"]
        self.assertEqual(views_rank[0]["video_id"], "v1")
        self.assertEqual(views_rank[0]["prior_rank"], 2)
        self.assertEqual(views_rank[0]["rank_delta"], 1)
        self.assertEqual([v["video_id"] for v in bundle["new_videos"]], ["v2"])

    def test_apply_mom_delta_skips_empty_stats(self) -> None:
        snapshot = {
            "subscriber_count": 0,
            "total_view_count": 0,
            "subscriber_delta": None,
            "subscriber_delta_pct": None,
            "total_view_delta": None,
            "total_view_delta_pct": None,
            "delta_baseline_date": None,
        }
        history = [
            {
                "collected_at": "2026-09-01 00:00:00",
                "subscriber_count": 1000,
                "total_view_count": 50000,
            }
        ]
        builder._apply_mom_delta(snapshot, history, date(2026, 10, 1))
        self.assertIsNone(snapshot["subscriber_delta"])
        self.assertIsNone(snapshot["delta_baseline_date"])

    def test_apply_wow_delta_skips_historical_week(self) -> None:
        snapshot = {
            "subscriber_count": 2000,
            "total_view_count": 100000,
            "subscriber_delta": None,
            "subscriber_delta_pct": None,
            "total_view_delta": None,
            "total_view_delta_pct": None,
            "delta_baseline_date": None,
        }
        history = [
            {
                "collected_at": "2026-07-05 00:00:00",
                "subscriber_count": 1000,
                "total_view_count": 50000,
            }
        ]
        # Regenerating an old week in October must not treat live stats as WoW.
        builder._apply_wow_delta(
            snapshot, history, date(2026, 7, 12), today=date(2026, 10, 19)
        )
        self.assertIsNone(snapshot["subscriber_delta"])
        self.assertIsNone(snapshot["delta_baseline_date"])

    def test_build_videos_meta_connection_error_degrades(self) -> None:
        bundle: dict = {"warnings": []}

        def boom(*_a: object, **_k: object) -> list:
            raise ConnectionError("dns fail")

        with patch("app.report.builder._call_api", side_effect=boom):
            meta = builder._build_videos_meta("UCtest", bundle)
        self.assertEqual(meta, {})
        self.assertTrue(any("dns fail" in w for w in bundle["warnings"]))


class CommitScriptOrderTest(unittest.TestCase):
    def test_commit_script_orders_add_before_pull(self) -> None:
        root = Path(__file__).resolve().parents[2]
        script = (root / ".github" / "scripts" / "commit-weekly-report.sh").read_text(
            encoding="utf-8"
        )
        # コメント行を除き、実コマンド行の出現順だけを検証する
        commands = [
            line.strip()
            for line in script.splitlines()
            if line.strip().startswith("git ")
        ]
        add_at = next(i for i, c in enumerate(commands) if c.startswith("git add "))
        commit_at = next(i for i, c in enumerate(commands) if c.startswith("git commit "))
        pull_at = next(
            i for i, c in enumerate(commands) if c.startswith("git pull --rebase ")
        )
        push_at = next(i for i, c in enumerate(commands) if c.startswith("git push "))
        self.assertLess(add_at, commit_at)
        self.assertLess(commit_at, pull_at)
        self.assertLess(pull_at, push_at)
        self.assertIn("Order (do not rearrange)", script)


class VideoPeriodMetricsTest(unittest.TestCase):
    def test_query_includes_sort_with_max_results(self) -> None:
        """dimensions=video + maxResults requires sort (Channel Reports rule)."""
        client = YouTubeAnalyticsClient()
        captured: dict = {}

        def fake_query(**kwargs: object) -> dict:
            captured.update(kwargs)
            return {
                "columnHeaders": [
                    {"name": "video"},
                    {"name": "views"},
                    {"name": "estimatedMinutesWatched"},
                    {"name": "averageViewDuration"},
                    {"name": "averageViewPercentage"},
                ],
                "rows": [["vid1", 10, 2, 30.0, 40.0]],
            }

        with patch.object(client, "_query", side_effect=fake_query):
            rows = client.video_period_metrics(
                ["vid1"], start_date="2026-10-04", end_date="2026-10-11"
            )
        self.assertEqual(captured.get("sort"), "-views")
        self.assertEqual(captured.get("maxResults"), 1)
        self.assertEqual(captured.get("dimensions"), "video")
        self.assertEqual(rows[0]["video_id"], "vid1")
        self.assertEqual(rows[0]["views"], 10)


class RendererSlackWeeklyTest(unittest.TestCase):
    def test_render_weekly_and_summary(self) -> None:
        bundle = {
            "meta": {
                "week": "2026-W41",
                "channel_id": "UCtest",
                "channel_title": "Test Channel",
                "week_start": "2026-10-05",
                "week_end": "2026-10-11",
                "prior_week_start": "2026-09-28",
                "prior_week_end": "2026-10-04",
                "generated_at": "2026-10-12",
            },
            "snapshot": {
                "subscriber_count": 1000,
                "total_view_count": 50000,
                "subscriber_delta": 10,
                "subscriber_delta_pct": 1.0,
                "total_view_delta": 200,
                "total_view_delta_pct": 0.4,
                "delta_baseline_date": "2026-10-04",
            },
            "period": {
                "views": 1200,
                "views_delta": 100,
                "views_delta_pct": 9.1,
                "minutes": 300,
                "minutes_delta": 20,
                "minutes_delta_pct": 7.1,
                "retention_pct": 35.0,
                "retention_delta_pp": 1.2,
            },
            "rankings": {
                "views": [
                    {
                        "rank": 1,
                        "prior_rank": 2,
                        "rank_delta": 1,
                        "views": 400,
                        "retention_pct": 40.0,
                        "engagement_pct": 1.2,
                        "published_at": "2026-09-01",
                        "title": "Video A",
                    }
                ],
                "minutes": [
                    {
                        "rank": 1,
                        "prior_rank": None,
                        "rank_delta": None,
                        "minutes": 90,
                        "retention_pct": 33.0,
                        "engagement_pct": 0.8,
                        "published_at": "2026-09-02",
                        "title": "Video B",
                    }
                ],
            },
            "new_videos": [
                {
                    "published_at": "2026-10-07",
                    "views": 80,
                    "retention_pct": 50.0,
                    "engagement_pct": 2.0,
                    "title": "New Clip",
                }
            ],
            "warnings": [],
        }
        sections = {
            "key_finding": "今週は再生が伸びた。",
            "next_actions": "### アクション #1: Shorts CTA を追加\n\n観察事実: …",
            "prior_validation": "対象なし",
        }
        md = renderer.render_weekly_report(bundle, sections)
        self.assertIn("# 週次インサイト 2026-W41", md)
        self.assertIn("週次スナップショット", md)
        self.assertIn("Video A", md)
        self.assertIn("Video B", md)
        self.assertIn("エンゲ%", md)
        self.assertIn("New Clip", md)
        self.assertIn("来週のアクション", md)

        summary = slack.build_weekly_summary(bundle, sections, "2026-W41")
        self.assertIn("週次インサイト 2026-W41", summary)
        self.assertIn("reports/weekly/2026-W41.md", summary)
        self.assertIn("アクション #1", summary)

    def test_render_notes_unfinalized_analytics(self) -> None:
        bundle = {
            "meta": {
                "week": "2026-W41",
                "channel_id": "UCtest",
                "channel_title": "Test",
                "week_start": "2026-10-05",
                "week_end": "2026-10-11",
                "prior_week_start": "2026-09-28",
                "prior_week_end": "2026-10-04",
                "analytics_start": "2026-10-05",
                "analytics_end": "2026-10-11",
                "analytics_may_include_unfinalized": True,
                "generated_at": "2026-10-15",
            },
            "snapshot": {},
            "period": {},
            "rankings": {"views": [], "minutes": []},
            "new_videos": [],
            "warnings": [],
            "author_failed": True,
        }
        sections = {
            "key_finding": "_fail_",
            "next_actions": "_fail_",
            "prior_validation": "_fail_",
        }
        md = renderer.render_weekly_report(bundle, sections)
        self.assertIn("未確定値を含む場合がある", md)
        self.assertIn("数値のみのレポート", md)
        self.assertIn("Analytics 照会（PT カレンダー・月〜日7日）", md)

        summary = slack.build_weekly_summary(bundle, sections, "2026-W41")
        self.assertIn("解釈生成に失敗", summary)


if __name__ == "__main__":
    unittest.main()
