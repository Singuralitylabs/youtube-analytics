"""Unit tests for weekly helpers and retry behaviour (no external APIs)."""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.report import renderer, slack  # noqa: E402
from app.report.retry import (  # noqa: E402
    is_retryable_api_error,
    is_retryable_gemini_error,
    with_retry,
)
from app.report.weeks import parse_iso_week, previous_iso_week  # noqa: E402


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


class RetryTest(unittest.TestCase):
    def test_retryable_gemini_503(self) -> None:
        class FakeErr(Exception):
            status_code = 503

        self.assertTrue(is_retryable_gemini_error(FakeErr("unavailable")))

    def test_non_retryable_gemini_401(self) -> None:
        class FakeErr(Exception):
            status_code = 401

        self.assertFalse(is_retryable_gemini_error(FakeErr("auth")))

    def test_with_retry_recovers_after_503(self) -> None:
        calls = {"n": 0}

        def flaky() -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                err = Exception("503 UNAVAILABLE high demand")
                raise err
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
                "minutes": [],
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
        self.assertIn("New Clip", md)
        self.assertIn("来週のアクション", md)

        summary = slack.build_weekly_summary(bundle, sections, "2026-W41")
        self.assertIn("週次インサイト 2026-W41", summary)
        self.assertIn("reports/weekly/2026-W41.md", summary)
        self.assertIn("アクション #1", summary)


if __name__ == "__main__":
    unittest.main()
