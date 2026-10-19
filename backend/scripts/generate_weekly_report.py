"""Generate the weekly YouTube analytics + countermeasures report.

Pipeline: builder (numbers) -> author (Gemini writes interpretation/対策) ->
renderer (assemble Markdown) -> write file -> Slack notify.

Usage (run from the ``backend/`` directory):

    # Full generate for the previous ISO week, write file + Slack state:
    python scripts/generate_weekly_report.py

    # Specific week, custom output dir, no Slack/state (local preview):
    python scripts/generate_weekly_report.py --week 2026-W41 --out /tmp/weekly --dry-run

    # Generate AND post Slack immediately (local end-to-end):
    python scripts/generate_weekly_report.py --notify

    # CI: post Slack from a previously generated state file (after commit/push):
    python scripts/generate_weekly_report.py --week 2026-W41 --notify-only

    # Render/data only, skip the Gemini call (offline pipeline check):
    python scripts/generate_weekly_report.py --dry-run --skip-author
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

# Allow `python scripts/generate_weekly_report.py` from the backend/ dir.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.report import author, builder, renderer, slack  # noqa: E402
from app.report.weeks import (  # noqa: E402
    is_week_label,
    load_prior_weekly_report,
    parse_iso_week,
    previous_iso_week,
)
from config.settings import get_settings  # noqa: E402


def _err(message: str) -> None:
    print(f"[generate-weekly] {message}", file=sys.stderr)


def _default_state_file() -> str:
    return os.path.join(tempfile.gettempdir(), "weekly_report_state.json")


def _resolve_output_dir(arg_out: str | None) -> str:
    if arg_out:
        return arg_out
    settings = get_settings()
    return os.path.join(REPO_ROOT, settings.REPORT_OUTPUT_DIR, "weekly")


def _load_playbook() -> str:
    path = os.path.join(REPO_ROOT, "docs", "analysis-playbook.md")
    try:
        with open(path, encoding="utf-8") as fp:
            return fp.read()
    except OSError as err:
        _err(f"プレイブックを読めません ({path}): {err}")
        return ""


def _placeholder_sections() -> dict[str, str]:
    note = "_（--skip-author のため未生成）_"
    return {key: note for key in author.WEEKLY_SECTION_KEYS}


def _failed_author_sections(err: Exception) -> dict[str, str]:
    note = f"_（解釈生成に失敗したため数値のみ掲載: {err}）_"
    return {key: note for key in author.WEEKLY_SECTION_KEYS}


def _do_notify_only(week: str, state_file: str) -> int:
    if not os.path.exists(state_file):
        _err(f"state ファイルが見つかりません: {state_file}")
        return 1
    with open(state_file, encoding="utf-8") as fp:
        state = json.load(fp)
    if state.get("week") != week:
        _err(f"state の週 ({state.get('week')}) が指定 ({week}) と一致しません")
        return 1
    slack.post(state["summary"])
    _err("Slack 通知を送信しました（--notify-only）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="週次インサイトレポート生成")
    parser.add_argument("--week", help="対象週 YYYY-Www（既定: 直前に終わった ISO 週・JST）")
    parser.add_argument(
        "--out", help="出力ディレクトリ（既定: <repo>/reports/weekly）"
    )
    parser.add_argument(
        "--state-file", default=_default_state_file(), help="Slack state JSON のパス"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ファイル生成のみ（Slack/state を書かない）",
    )
    parser.add_argument(
        "--skip-author",
        action="store_true",
        help="Gemini 呼び出しをスキップ（データ/描画のみ確認）",
    )
    parser.add_argument(
        "--notify",
        action="store_true",
        help="生成後ただちに Slack 通知（ローカル一括実行用）",
    )
    parser.add_argument(
        "--notify-only",
        action="store_true",
        help="生成せず state ファイルから Slack 通知（CI のコミット後ステップ用）",
    )
    args = parser.parse_args(argv)

    if args.week:
        week = args.week
        if not is_week_label(week):
            _err(f"--week の形式が不正です: {week}（YYYY-Www）")
            return 2
        try:
            week_start, week_end = parse_iso_week(week)
        except ValueError as err:
            _err(str(err))
            return 2
    else:
        week, week_start, week_end = previous_iso_week()

    output_dir = _resolve_output_dir(args.out)

    if args.notify_only:
        return _do_notify_only(week, args.state_file)

    # ---- Generate ----------------------------------------------------------
    _err(
        f"データ収集中… (week={week}, {week_start.isoformat()}〜{week_end.isoformat()})"
    )
    bundle = builder.build_weekly_bundle(
        week_start, week_end, week_label=week
    )
    if bundle.get("warnings"):
        _err(f"警告 {len(bundle['warnings'])} 件（レポート末尾に記載）")

    if args.skip_author:
        sections = _placeholder_sections()
    else:
        playbook = _load_playbook()
        prior = load_prior_weekly_report(output_dir, week)
        _err(f"前週レポート: {'あり' if prior else 'なし（初回/スキップ週扱い）'}")
        try:
            sections = author.author_weekly_report(
                bundle, playbook_text=playbook, prior_report_text=prior
            )
        except Exception as err:  # noqa: BLE001 - degrade, don't lose the week.
            _err(f"解釈生成に失敗: {err}（数値のみでレポートを継続）")
            bundle["warnings"].append(f"解釈セクション生成失敗（Gemini）: {err}")
            bundle["author_failed"] = True
            sections = _failed_author_sections(err)

    markdown = renderer.render_weekly_report(bundle, sections)
    path = renderer.write_report(markdown, output_dir, week)
    _err(f"レポートを書き出しました: {path}")

    summary = slack.build_weekly_summary(bundle, sections, week)

    if not args.dry_run:
        with open(args.state_file, "w", encoding="utf-8") as fp:
            json.dump({"week": week, "summary": summary}, fp, ensure_ascii=False)
        _err(f"Slack state を保存: {args.state_file}")

    if args.notify and not args.dry_run:
        slack.post(summary)
        _err("Slack 通知を送信しました（--notify）")

    print(path)  # machine-parseable: the report path on stdout
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
