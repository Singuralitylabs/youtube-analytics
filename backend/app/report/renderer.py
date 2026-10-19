"""Assemble the final monthly report Markdown.

Deterministic tables (snapshot, rankings, split-rank matrix) are rendered here
from the data bundle so the numbers are exact; the interpretive sections come
from ``author.author_report``. The output follows the canonical monthly format
in ``docs/analysis-playbook.md`` §6 and the example ``reports/2026-05.md``.
"""

from __future__ import annotations

import os
from typing import Any

# Fixed interpretation text per split-rank quadrant (from playbook Step 2).
_QUADRANTS = [
    ("high_views_high_retention", "再生高 × 維持高（王道ヒット）", "同テーマで深掘り or 続編の価値が高い"),
    ("high_views_low_retention", "再生高 × 維持低（釣り疑い）", "タイトル文言・サムネ整合性をチェック"),
    ("low_views_high_retention", "再生低 × 維持高（隠れた良作）", "サムネ刷新・内部リンク・関連動画戦略の最有力候補"),
    ("low_views_low_retention", "再生低 × 維持低（ミスマッチ）", "撤退判断 or 切り口変更"),
]


def _num(value: Any) -> str:
    """Thousands-separated integer, or '—' when missing."""
    if value is None:
        return "—"
    try:
        return f"{int(round(float(value))):,}"
    except (ValueError, TypeError):
        return "—"


def _pct(value: Any, digits: int = 1) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}%"
    except (ValueError, TypeError):
        return "—"


def _delta(value: Any, pct: Any) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    base = f"{sign}{_num(value)}"
    if pct is not None:
        base += f"（{sign}{float(pct):.1f}%）"
    return base


def render_report(bundle: dict[str, Any], sections: dict[str, str]) -> str:
    meta = bundle.get("meta", {})
    parts: list[str] = []

    title = meta.get("channel_title") or meta.get("channel_id", "")
    parts.append(f"# 月次インサイト {meta.get('month', '')}")
    parts.append("")
    parts.append(f"> 分析対象: {title}（{meta.get('channel_id', '')}）")
    parts.append(
        f"> 集計期間: 直近{meta.get('window_days', 90)}日"
        f"（{meta.get('window_start', '')} 〜 {meta.get('window_end', '')}）"
    )
    parts.append(f"> 分析実行日: {meta.get('generated_at', '')}")
    if bundle.get("warnings"):
        parts.append(
            f"> 注: データ取得時に {len(bundle['warnings'])} 件の警告あり"
            "（末尾「データ取得メモ」参照）"
        )
    parts.append("")
    parts.append("---")
    parts.append("")

    parts.append(_render_snapshot(bundle))
    parts.append(_section("1. 最重要発見", sections.get("key_finding", "")))
    parts.append(_render_rankings(bundle, sections.get("rankings_note", "")))
    parts.append(_section("3. 個別動画ドリルダウン", sections.get("drilldowns", "")))
    parts.append(_section("4. パターン別の発見", sections.get("patterns", "")))
    parts.append(_section("5. 今月の仮説カード", sections.get("hypotheses", "")))
    parts.append(_section("6. 先月の仮説検証", sections.get("prior_validation", "")))
    parts.append(_section("7. 次の機能化候補", sections.get("feature_candidates", "")))
    parts.append(_section("8. 来月の検証ポイント", sections.get("next_month", "")))

    if bundle.get("warnings"):
        parts.append(_render_warnings(bundle["warnings"]))

    return "\n".join(parts).rstrip() + "\n"


def _section(heading: str, body: str) -> str:
    body = (body or "_（生成されませんでした）_").strip()
    return f"## {heading}\n\n{body}\n\n---\n"


def _render_snapshot(bundle: dict[str, Any]) -> str:
    s = bundle.get("snapshot", {})
    lines = [
        "## 0. 全体スナップショット",
        "",
        "| 指標 | 値 | 前月比 |",
        "|---|---:|---:|",
        f"| 登録者数 | {_num(s.get('subscriber_count'))} | "
        f"{_delta(s.get('subscriber_delta'), s.get('subscriber_delta_pct'))} |",
        f"| 総再生数（累計） | {_num(s.get('total_view_count'))} | "
        f"{_delta(s.get('total_view_delta'), s.get('total_view_delta_pct'))} |",
        f"| 公開動画数 | {_num(s.get('video_count'))} | — |",
        f"| 平均1動画あたり累計再生数 | {_num(s.get('avg_views_per_video'))} | — |",
    ]
    if s.get("delta_baseline_date"):
        lines.append("")
        lines.append(f"> 前月比の基準日: {s['delta_baseline_date']}（Sheets スナップショット）")
    else:
        lines.append("")
        lines.append("> 前月比: Sheets 履歴が不足のため未算出（`POST /api/collect` の継続記録が前提）")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _render_rankings(bundle: dict[str, Any], note: str) -> str:
    rk = bundle.get("rankings", {})
    days = bundle.get("meta", {}).get("window_days", 90)
    out = [f"## 2. ランキング所見（直近{days}日）", ""]

    out.append("### views（再生数）Top10")
    out.append("")
    out.append("| # | 再生 | 維持率 | エンゲ% | 公開日 | タイトル |")
    out.append("|---|---:|---:|---:|---|---|")
    for r in rk.get("views", [])[:10]:
        out.append(
            f"| {r['rank']} | {_num(r.get('views'))} | "
            f"{_pct(r.get('retention_pct'))} | {_pct(r.get('engagement_pct'), 2)} | "
            f"{r.get('published_at', '')} | {_clean(r.get('title'))} |"
        )
    out.append("")

    out.append("### estimatedMinutesWatched（総視聴時間）Top10")
    out.append("")
    out.append("| # | 視聴分 | 維持率 | 公開日 | タイトル |")
    out.append("|---|---:|---:|---|---|")
    for r in rk.get("minutes", [])[:10]:
        out.append(
            f"| {r['rank']} | {_num(r.get('minutes'))} | "
            f"{_pct(r.get('retention_pct'))} | {r.get('published_at', '')} | "
            f"{_clean(r.get('title'))} |"
        )
    out.append("")

    out.append("### 平均視聴維持率（averageViewPercentage）Top10")
    out.append("")
    out.append("> 注: 維持率は動画長に強く依存（短尺ほど高くなりやすい）。長さの違う動画間の単純比較は避けること。")
    out.append("")
    out.append("| # | 維持率 | 再生 | 動画長(秒) | 公開日 | タイトル |")
    out.append("|---|---:|---:|---:|---|---|")
    for idx, r in enumerate(rk.get("retention", [])[:10], start=1):
        out.append(
            f"| {idx} | {_pct(r.get('retention_pct'))} | {_num(r.get('views'))} | "
            f"{_num(r.get('duration_sec'))} | {r.get('published_at', '')} | "
            f"{_clean(r.get('title'))} |"
        )
    out.append("")

    out.append("### 指標順位の食い違い（プレイブック Step 2）")
    out.append("")
    out.append("| パターン | 動画 | 次のアクション |")
    out.append("|---|---|---|")
    split = bundle.get("split_rank", {})
    for key, label, action in _QUADRANTS:
        vids = split.get(key, [])
        cell = "／".join(
            f"{_clean(v.get('title'))}（{_num(v.get('views'))}re / {_pct(v.get('retention_pct'))}）"
            for v in vids[:3]
        ) or "—"
        out.append(f"| {label} | {cell} | {action} |")
    out.append("")

    if note.strip():
        out.append(note.strip())
        out.append("")
    out.append("---")
    out.append("")
    return "\n".join(out)


def _render_warnings(warnings: list[str]) -> str:
    lines = ["## データ取得メモ", "", "レポート生成時に以下の警告が発生しました（該当箇所は空欄/欠損）:", ""]
    lines.extend(f"- {w}" for w in warnings)
    lines.append("")
    return "\n".join(lines)


def _clean(title: Any) -> str:
    """Escape pipe characters so titles don't break Markdown tables."""
    return str(title or "").replace("|", "\\|").strip()


def write_report(markdown: str, output_dir: str, label: str) -> str:
    """Write the report to ``{output_dir}/{label}.md`` and return its path.

    ``label`` is ``YYYY-MM`` for monthly reports or ``YYYY-Www`` for weekly.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{label}.md")
    with open(path, "w", encoding="utf-8") as fp:
        fp.write(markdown)
    return path


def render_weekly_report(bundle: dict[str, Any], sections: dict[str, str]) -> str:
    """Assemble the lighter weekly report Markdown."""
    meta = bundle.get("meta", {})
    parts: list[str] = []

    title = meta.get("channel_title") or meta.get("channel_id", "")
    parts.append(f"# 週次インサイト {meta.get('week', '')}")
    parts.append("")
    parts.append(f"> 分析対象: {title}（{meta.get('channel_id', '')}）")
    parts.append(
        f"> 集計期間: {meta.get('week_start', '')} 〜 {meta.get('week_end', '')}"
        f"（前週比対象: {meta.get('prior_week_start', '')} 〜 "
        f"{meta.get('prior_week_end', '')}）"
    )
    parts.append(f"> 分析実行日: {meta.get('generated_at', '')}")
    if meta.get("analytics_start") and meta.get("analytics_end"):
        parts.append(
            f"> Analytics 照会（PT カレンダー・月〜日7日）: "
            f"{meta.get('analytics_start')} 〜 {meta.get('analytics_end')}"
        )
    if meta.get("analytics_may_include_unfinalized"):
        parts.append(
            "> 注: YouTube Analytics は確定に最大48〜72時間かかるため、"
            "週末付近は未確定値を含む場合がある"
            "（定期実行は水曜 UTC で緩和）"
        )
    if bundle.get("warnings"):
        parts.append(
            f"> 注: データ取得時に {len(bundle['warnings'])} 件の警告あり"
            "（末尾「データ取得メモ」参照）"
        )
    if bundle.get("author_failed"):
        parts.append("> 注: 解釈生成に失敗したため数値のみのレポートです")
    parts.append("")
    parts.append("---")
    parts.append("")

    parts.append(_render_weekly_snapshot(bundle))
    parts.append(_section("1. 今週の最重要ポイント", sections.get("key_finding", "")))
    parts.append(_render_weekly_rankings(bundle))
    parts.append(_render_new_videos(bundle))
    parts.append(_section("4. 来週のアクション", sections.get("next_actions", "")))
    parts.append(
        _section("5. 先週アクションの検証", sections.get("prior_validation", ""))
    )

    if bundle.get("warnings"):
        parts.append(_render_warnings(bundle["warnings"]))

    return "\n".join(parts).rstrip() + "\n"


def _render_weekly_snapshot(bundle: dict[str, Any]) -> str:
    s = bundle.get("snapshot", {})
    p = bundle.get("period", {})
    lines = [
        "## 0. 週次スナップショット",
        "",
        "| 指標 | 値 | 前週比 |",
        "|---|---:|---:|",
        f"| 登録者数 | {_num(s.get('subscriber_count'))} | "
        f"{_delta(s.get('subscriber_delta'), s.get('subscriber_delta_pct'))} |",
        f"| 総再生数（累計） | {_num(s.get('total_view_count'))} | "
        f"{_delta(s.get('total_view_delta'), s.get('total_view_delta_pct'))} |",
        f"| 当週の再生数 | {_num(p.get('views'))} | "
        f"{_delta(p.get('views_delta'), p.get('views_delta_pct'))} |",
        f"| 当週の総視聴時間（分） | {_num(p.get('minutes'))} | "
        f"{_delta(p.get('minutes_delta'), p.get('minutes_delta_pct'))} |",
        f"| 当週の平均維持率 | {_pct(p.get('retention_pct'))} | "
        f"{_pp_delta(p.get('retention_delta_pp'))} |",
    ]
    if s.get("delta_baseline_date"):
        lines.append("")
        lines.append(
            f"> 登録者・総再生の前週比基準日: {s['delta_baseline_date']}"
            "（Sheets スナップショット）"
        )
    else:
        lines.append("")
        lines.append(
            "> 登録者・総再生の前週比: Sheets 履歴が不足のため未算出"
            "（`POST /api/collect` の継続記録が前提）"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _pp_delta(value: Any) -> str:
    """Format a percentage-point delta (retention WoW)."""
    if value is None:
        return "—"
    try:
        num = float(value)
    except (ValueError, TypeError):
        return "—"
    sign = "+" if num >= 0 else ""
    return f"{sign}{num:.1f}pp"


def _render_weekly_rankings(bundle: dict[str, Any]) -> str:
    rk = bundle.get("rankings", {})
    out = ["## 2. 当週ランキング", ""]

    out.append("### 再生数 Top5")
    out.append("")
    out.append("| # | 前週 | 再生 | 維持率 | エンゲ% | 公開日 | タイトル |")
    out.append("|---|---|---:|---:|---:|---|---|")
    for r in rk.get("views", [])[:5]:
        out.append(
            f"| {r['rank']} | {_rank_change(r)} | {_num(r.get('views'))} | "
            f"{_pct(r.get('retention_pct'))} | {_pct(r.get('engagement_pct'), 2)} | "
            f"{r.get('published_at', '')} | {_clean(r.get('title'))} |"
        )
    out.append("")

    out.append("### 視聴時間 Top5")
    out.append("")
    out.append("| # | 前週 | 視聴分 | 維持率 | エンゲ% | 公開日 | タイトル |")
    out.append("|---|---|---:|---:|---:|---|---|")
    for r in rk.get("minutes", [])[:5]:
        out.append(
            f"| {r['rank']} | {_rank_change(r)} | {_num(r.get('minutes'))} | "
            f"{_pct(r.get('retention_pct'))} | {_pct(r.get('engagement_pct'), 2)} | "
            f"{r.get('published_at', '')} | {_clean(r.get('title'))} |"
        )
    out.append("")
    out.append("---")
    out.append("")
    return "\n".join(out)


def _rank_change(row: dict[str, Any]) -> str:
    prior = row.get("prior_rank")
    delta = row.get("rank_delta")
    if prior is None:
        return "NEW"
    if delta is None or delta == 0:
        return f"{prior}（→）"
    sign = "+" if delta > 0 else ""
    return f"{prior}（{sign}{delta}）"


def _render_new_videos(bundle: dict[str, Any]) -> str:
    rows = bundle.get("new_videos") or []
    out = ["## 3. 新規公開動画の初動", ""]
    if not rows:
        out.append("_当週に公開された動画はありません。_")
        out.append("")
        out.append("---")
        out.append("")
        return "\n".join(out)

    out.append("| 公開日 | 再生 | 維持率 | エンゲ% | タイトル |")
    out.append("|---|---:|---:|---:|---|")
    for r in rows:
        out.append(
            f"| {r.get('published_at', '')} | {_num(r.get('views'))} | "
            f"{_pct(r.get('retention_pct'))} | {_pct(r.get('engagement_pct'), 2)} | "
            f"{_clean(r.get('title'))} |"
        )
    out.append("")
    out.append("---")
    out.append("")
    return "\n".join(out)
