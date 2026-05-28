"""Generate the monthly YouTube analytics + countermeasures report.

Pipeline: builder (numbers) -> author (Gemini writes interpretation/対策) ->
renderer (assemble Markdown) -> write file -> Slack notify.

Usage (run from the ``backend/`` directory):

    # Full generate for the current month, write file + Slack state:
    python scripts/generate_monthly_report.py

    # Specific month, custom output dir, no Slack/state (local preview):
    python scripts/generate_monthly_report.py --month 2026-05 --out /tmp/reports --dry-run

    # Generate AND post Slack immediately (local end-to-end):
    python scripts/generate_monthly_report.py --notify

    # CI: post Slack from a previously generated state file (after commit/push):
    python scripts/generate_monthly_report.py --month 2026-05 --notify-only

    # Render/data only, skip the Gemini call (offline pipeline check):
    python scripts/generate_monthly_report.py --dry-run --skip-author
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date

# Allow `python scripts/generate_monthly_report.py` from the backend/ dir.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BACKEND_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.report import author, builder, renderer, slack  # noqa: E402
from config.settings import get_settings  # noqa: E402

_MONTH_RE = re.compile(r"^(\d{4})-(\d{2})$")
_REPORT_RE = re.compile(r"^(\d{4}-\d{2})\.md$")


def _err(message: str) -> None:
    print(f"[generate] {message}", file=sys.stderr)


def _default_state_file() -> str:
    return os.path.join(tempfile.gettempdir(), "monthly_report_state.json")


def _resolve_output_dir(arg_out: str | None) -> str:
    if arg_out:
        return arg_out
    settings = get_settings()
    return os.path.join(REPO_ROOT, settings.REPORT_OUTPUT_DIR)


def _load_playbook() -> str:
    path = os.path.join(REPO_ROOT, "docs", "analysis-playbook.md")
    try:
        with open(path, encoding="utf-8") as fp:
            return fp.read()
    except OSError as err:
        _err(f"プレイブックを読めません ({path}): {err}")
        return ""


def _load_prior_report(output_dir: str, current_month: str) -> str | None:
    """Return the text of the most recent report strictly before current_month."""
    if not os.path.isdir(output_dir):
        return None
    candidates: list[str] = []
    for name in os.listdir(output_dir):
        m = _REPORT_RE.match(name)
        if m and m.group(1) < current_month:
            candidates.append(m.group(1))
    if not candidates:
        return None
    latest = max(candidates)
    with open(os.path.join(output_dir, f"{latest}.md"), encoding="utf-8") as fp:
        return fp.read()


def _placeholder_sections() -> dict[str, str]:
    note = "_（--skip-author のため未生成）_"
    return {key: note for key in author.SECTION_KEYS}


def _do_notify_only(month: str, state_file: str) -> int:
    if not os.path.exists(state_file):
        _err(f"state ファイルが見つかりません: {state_file}")
        return 1
    with open(state_file, encoding="utf-8") as fp:
        state = json.load(fp)
    if state.get("month") != month:
        _err(f"state の月 ({state.get('month')}) が指定 ({month}) と一致しません")
        return 1
    slack.post(state["summary"])
    _err("Slack 通知を送信しました（--notify-only）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="月次インサイトレポート生成")
    parser.add_argument("--month", help="対象月 YYYY-MM（既定: 当月）")
    parser.add_argument("--out", help="出力ディレクトリ（既定: <repo>/reports）")
    parser.add_argument("--days", type=int, default=90, help="分析窓（最大90）")
    parser.add_argument(
        "--drilldowns", type=int, default=6, help="ドリルダウンする動画数"
    )
    parser.add_argument(
        "--state-file", default=_default_state_file(), help="Slack state JSON のパス"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="ファイル生成のみ（Slack/state を書かない）",
    )
    parser.add_argument(
        "--skip-author", action="store_true",
        help="Gemini 呼び出しをスキップ（データ/描画のみ確認）",
    )
    parser.add_argument(
        "--notify", action="store_true",
        help="生成後ただちに Slack 通知（ローカル一括実行用）",
    )
    parser.add_argument(
        "--notify-only", action="store_true",
        help="生成せず state ファイルから Slack 通知（CI のコミット後ステップ用）",
    )
    args = parser.parse_args(argv)

    month = args.month or date.today().strftime("%Y-%m")
    if not _MONTH_RE.match(month):
        _err(f"--month の形式が不正です: {month}（YYYY-MM）")
        return 2
    if args.days < 1 or args.days > 90:
        _err("--days は 1〜90 で指定してください")
        return 2

    output_dir = _resolve_output_dir(args.out)

    if args.notify_only:
        return _do_notify_only(month, args.state_file)

    # ---- Generate ----------------------------------------------------------
    _err(f"データ収集中… (month={month}, days={args.days})")
    bundle = builder.build_data_bundle(
        days=args.days, drilldown_count=args.drilldowns, month=month
    )
    if bundle.get("warnings"):
        _err(f"警告 {len(bundle['warnings'])} 件（レポート末尾に記載）")

    if args.skip_author:
        sections = _placeholder_sections()
    else:
        playbook = _load_playbook()
        prior = _load_prior_report(output_dir, month)
        _err(f"前月レポート: {'あり' if prior else 'なし（初回扱い）'}")
        sections = author.author_report(
            bundle, playbook_text=playbook, prior_report_text=prior
        )

    markdown = renderer.render_report(bundle, sections)
    path = renderer.write_report(markdown, output_dir, month)
    _err(f"レポートを書き出しました: {path}")

    summary = slack.build_summary(bundle, sections, month)

    if not args.dry_run:
        with open(args.state_file, "w", encoding="utf-8") as fp:
            json.dump({"month": month, "summary": summary}, fp, ensure_ascii=False)
        _err(f"Slack state を保存: {args.state_file}")

    if args.notify and not args.dry_run:
        slack.post(summary)
        _err("Slack 通知を送信しました（--notify）")

    print(path)  # machine-parseable: the report path on stdout
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
