"""Build and post the monthly Slack notification (Incoming Webhook).

The message is a concise summary (snapshot one-liner, key-finding lead, and the
hypothesis/対策 headlines) plus a link to the committed report on GitHub. The
full report lives in the repo; Slack carries only the digest. Uses stdlib
``urllib`` so there is no extra dependency.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from typing import Any

from config.settings import get_settings


def _log(message: str) -> None:
    print(f"[slack] {message}", file=sys.stderr)


def github_report_url(label: str, *, subdir: str = "") -> str:
    """Construct the GitHub blob URL for a committed report.

    ``label`` is the file stem (``YYYY-MM`` or ``YYYY-Www``). ``subdir`` is an
    optional path under ``REPORT_OUTPUT_DIR`` (e.g. ``weekly``).
    """
    s = get_settings()
    base = s.REPORT_OUTPUT_DIR.strip("/")
    if subdir:
        path = f"{base}/{subdir.strip('/')}/{label}.md"
    else:
        path = f"{base}/{label}.md"
    return f"https://github.com/{s.GITHUB_REPO}/blob/{s.GITHUB_BRANCH}/{path}"


def build_summary(
    bundle: dict[str, Any], sections: dict[str, str], month: str
) -> str:
    """Assemble the monthly Slack mrkdwn message body."""
    meta = bundle.get("meta", {})
    snap = bundle.get("snapshot", {})
    title = meta.get("channel_title") or meta.get("channel_id", "")

    lines = [f":bar_chart: *月次インサイト {month}* — {title}"]

    # When Gemini authoring failed we ship a numbers-only report; the interpretive
    # fields hold a failure note, so skip the key-finding / hypothesis snippets
    # (they would otherwise surface the failure text as if it were an insight).
    degraded = bool(bundle.get("author_failed"))

    sub = _fmt_delta(snap.get("subscriber_count"), snap.get("subscriber_delta"))
    views = _fmt_delta(snap.get("total_view_count"), snap.get("total_view_delta"))
    lines.append(f"登録者 {sub} / 総再生 {views} / 動画 {_int(snap.get('video_count'))}本")

    if degraded:
        lines.append("")
        lines.append(":warning: *解釈生成に失敗したため数値のみのレポートです*")
    else:
        snippet = _lead_sentence(sections.get("key_finding", ""))
        if snippet:
            lines.append("")
            lines.append(f"*最重要発見*: {snippet}")

        headlines = _hypothesis_headlines(sections.get("hypotheses", ""))
        if headlines:
            lines.append("")
            lines.append("*今月の対策（仮説）*:")
            lines.extend(f"• {h}" for h in headlines)

    url = github_report_url(month)
    lines.append("")
    lines.append(f"<{url}|レポート全文を見る> 📄")

    if bundle.get("warnings"):
        lines.append(f"_（データ取得時の警告 {len(bundle['warnings'])} 件あり）_")

    return "\n".join(lines)


def build_weekly_summary(
    bundle: dict[str, Any], sections: dict[str, str], week: str
) -> str:
    """Assemble the weekly Slack mrkdwn message body."""
    meta = bundle.get("meta", {})
    snap = bundle.get("snapshot", {})
    period = bundle.get("period", {})
    title = meta.get("channel_title") or meta.get("channel_id", "")

    lines = [f":calendar: *週次インサイト {week}* — {title}"]
    degraded = bool(bundle.get("author_failed"))

    sub = _fmt_delta(snap.get("subscriber_count"), snap.get("subscriber_delta"))
    week_views = _fmt_delta(period.get("views"), period.get("views_delta"))
    lines.append(
        f"登録者 {sub} / 当週再生 {week_views} / "
        f"維持率 {_fmt_pct(period.get('retention_pct'))}"
    )

    if degraded:
        lines.append("")
        lines.append(":warning: *解釈生成に失敗したため数値のみのレポートです*")
    else:
        snippet = _lead_sentence(sections.get("key_finding", ""))
        if snippet:
            lines.append("")
            lines.append(f"*今週の最重要ポイント*: {snippet}")

        headlines = _action_headlines(sections.get("next_actions", ""))
        if headlines:
            lines.append("")
            lines.append("*来週のアクション*:")
            lines.extend(f"• {h}" for h in headlines)

    url = github_report_url(week, subdir="weekly")
    lines.append("")
    lines.append(f"<{url}|レポート全文を見る> 📄")

    if bundle.get("warnings"):
        lines.append(f"_（データ取得時の警告 {len(bundle['warnings'])} 件あり）_")

    return "\n".join(lines)


def post(text: str) -> None:
    """POST a message to the configured Slack Incoming Webhook."""
    s = get_settings()
    if not s.SLACK_WEBHOOK_URL:
        raise RuntimeError(
            "SLACK_WEBHOOK_URL が未設定です。.env または GitHub Secrets に設定してください。"
        )
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        s.SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if body.strip() != "ok":
                _log(f"Slack 応答: {body!r}")
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Slack 通知に失敗 ({err.code}): {detail}") from err


def notify(bundle: dict[str, Any], sections: dict[str, str], month: str) -> None:
    text = build_summary(bundle, sections, month)
    post(text)
    _log("Slack 通知を送信しました")


# --------------------------------------------------------------------------- #
# Summary extraction helpers
# --------------------------------------------------------------------------- #
def _int(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return "—"


def _fmt_delta(current: Any, delta: Any) -> str:
    base = _int(current)
    if delta is None:
        return base
    sign = "+" if delta >= 0 else ""
    return f"{base}（{sign}{_int(delta)}）"


def _lead_sentence(markdown: str, limit: int = 180) -> str:
    """First meaningful line of the key finding (skips headings/blank lines)."""
    for raw in markdown.splitlines():
        line = raw.strip().lstrip("#").strip().lstrip("*").strip()
        if line and not line.startswith(("|", "-", ">")):
            return line[:limit] + ("…" if len(line) > limit else "")
    return ""


def _hypothesis_headlines(markdown: str, limit: int = 3) -> list[str]:
    """Pull descriptive '### 仮説 #N: …' headings from the hypotheses section.

    Skips the 'カード/仮説カード [日付]' wrapper heading and any bare '仮説 #N'
    heading with no description, so the Slack digest carries the actual
    countermeasure text rather than uninformative labels.
    """
    return _markdown_headlines(
        markdown, limit=limit, bare_re=r"仮説\s*#?\d+[:：]?"
    )


def _action_headlines(markdown: str, limit: int = 2) -> list[str]:
    """Pull descriptive '### アクション #N: …' headings from next_actions."""
    return _markdown_headlines(
        markdown, limit=limit, bare_re=r"アクション\s*#?\d+[:：]?"
    )


def _markdown_headlines(
    markdown: str, *, limit: int, bare_re: str
) -> list[str]:
    headlines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line.startswith("###"):
            continue
        text = line.lstrip("#").strip()
        if not text or _is_wrapper_heading(text, bare_re=bare_re):
            continue
        headlines.append(text)
        if len(headlines) >= limit:
            break
    return headlines


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f}%"
    except (ValueError, TypeError):
        return "—"


def _is_wrapper_heading(text: str, *, bare_re: str = r"仮説\s*#?\d+[:：]?") -> bool:
    """True for generic wrapper/label headings that carry no insight."""
    # "仮説カード 2026-05-28" etc.
    if text.replace("【", "").replace("】", "").startswith("仮説カード"):
        return True
    # Bare "仮説 #1" / "アクション #1" with no trailing description.
    return bool(re.fullmatch(bare_re, text))
