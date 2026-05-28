"""Author the interpretive report sections with the Gemini API (free tier).

This is the *reasoning* half of the hybrid generator. The deterministic numbers
come from ``builder.build_data_bundle``; here we hand those numbers (plus the
analysis playbook and last month's report) to Gemini and ask it to write the
sections that require judgement: key finding, drilldown interpretation, pattern
findings, hypothesis cards (対策), prior-hypothesis validation, and next steps.

Notes on the API usage (Google Gen AI SDK, ``google-genai``):

* JSON output is enforced via ``response_mime_type='application/json'`` +
  ``response_json_schema`` (the 8 section keys), so no parsing tricks needed.
* The playbook goes into ``system_instruction``; the data bundle + prior report
  go into ``contents``.

The default model is ``gemini-2.5-flash`` (free-tier friendly), overridable via
``GEMINI_MODEL``.

Privacy note: the Gemini API free tier may use submitted content to improve
Google's products. The report contains channel-private data — use a paid tier or
a no-logging configuration if that is a concern (see docs/monthly-report.md).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from config.settings import get_settings

# Keys the model must return. Each maps to a section the renderer slots in.
SECTION_KEYS = (
    "key_finding",        # 1. 最重要発見
    "rankings_note",      # 2. ランキング所見（表の下に付す観察）
    "drilldowns",         # 3. 個別動画ドリルダウン
    "patterns",           # 4. パターン別の発見（A〜F）
    "hypotheses",         # 5. 今月の仮説カード（対策）
    "prior_validation",   # 6. 先月の仮説検証
    "feature_candidates", # 7. 次の機能化候補
    "next_month",         # 8. 来月の検証ポイント
)

_SYSTEM_INSTRUCTIONS = """\
あなたは YouTube チャンネル分析の専門家です。与えられた「確定データ（JSON）」と\
「分析プレイブック」に厳密に従い、教育・解説系チャンネルの月次インサイトレポートの\
**解釈・対策セクションのみ**を日本語で執筆します。

厳守事項:
- 数値は与えられた確定データの値だけを使う。**データに無い数値を創作しない**。
- プレイブックの方法論（KPIツリー、Step2の判定マトリクス、アンチパターン）に従う。
- 維持率は動画長に強く依存する。長さの異なる動画間の維持率比較は避け、必要なら断りを入れる。
- 「対策（打ち手）」は具体的・実行可能にし、検証指標と期限・目標値をセットで書く（プレイブック6章の仮説カード形式）。
- 同時に試す打ち手は最大2つに絞る。
- 誇大表現（"圧倒的""完璧"等）を使わず、根拠（数値）に基づく professional な記述にする。
- demographics が空配列の動画は匿名化のため取得不可と明記する。
- 各セクションの値の中では `##`（セクション見出し）を使わず `###` 以下のみ使う（セクション見出しはレンダラが付与する）。
"""


def _log(message: str) -> None:
    print(f"[author] {message}", file=sys.stderr)


def author_report(
    bundle: dict[str, Any],
    *,
    playbook_text: str,
    prior_report_text: str | None,
) -> dict[str, str]:
    """Call Gemini and return a mapping of section-key -> Markdown body.

    Raises:
        RuntimeError: if GEMINI_API_KEY is unset or the response can't be
            parsed into the expected sections.
    """
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY が未設定です。.env または GitHub Secrets に設定してください。"
            "（Google AI Studio https://aistudio.google.com/apikey で無料発行）"
        )

    # Imported lazily so the builder/renderer pipeline (and --skip-author) runs
    # without the google-genai SDK installed.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    system_instruction = (
        _SYSTEM_INSTRUCTIONS + "\n\n# 分析プレイブック\n\n" + playbook_text
    )
    user_prompt = _build_user_prompt(bundle, prior_report_text)
    schema = {
        "type": "object",
        "properties": {key: {"type": "string"} for key in SECTION_KEYS},
        "required": list(SECTION_KEYS),
    }

    _log(f"model={settings.GEMINI_MODEL} で執筆中…")
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.4,
            max_output_tokens=16384,
            response_mime_type="application/json",
            response_json_schema=schema,
        ),
    )

    usage = getattr(response, "usage_metadata", None)
    if usage is not None:
        _log(
            "tokens "
            f"prompt={getattr(usage, 'prompt_token_count', '?')} "
            f"out={getattr(usage, 'candidates_token_count', '?')}"
        )

    text = response.text
    if not text:
        raise RuntimeError("Gemini 応答が空です（max_output_tokens 超過の可能性）")
    data = _parse_json(text)
    return _normalize_sections(data)


def _parse_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from the model output, tolerating stray wrapping."""
    candidate = text.strip()
    if candidate.startswith("```"):
        # Strip a ```json ... ``` fence if the model added one.
        candidate = candidate.split("```", 2)[1]
        if candidate.startswith("json"):
            candidate = candidate[4:]
        candidate = candidate.strip().rstrip("`").strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(candidate[start : end + 1])
        raise RuntimeError("Gemini 応答を JSON として解釈できませんでした")


def _normalize_sections(data: dict[str, Any]) -> dict[str, str]:
    sections: dict[str, str] = {}
    for key in SECTION_KEYS:
        value = data.get(key, "")
        sections[key] = value.strip() if isinstance(value, str) else str(value)
    return sections


def _build_user_prompt(
    bundle: dict[str, Any], prior_report_text: str | None
) -> str:
    compact = _compact_bundle(bundle)
    data_json = json.dumps(compact, ensure_ascii=False, indent=2)

    prior_block = (
        f"## 先月のレポート全文（仮説検証の材料）\n\n{prior_report_text}"
        if prior_report_text
        else "## 先月のレポート\n\n（初回のため存在しません。`prior_validation` は"
        "「初回のため対象なし」と記載してください。`key_finding` を分厚く書いてください。）"
    )

    key_list = "\n".join(f"  - {k}" for k in SECTION_KEYS)
    return f"""\
以下の確定データとプレイブックに基づき、月次インサイトレポートの解釈・対策セクションを執筆してください。

# 確定データ（JSON）

```json
{data_json}
```

{prior_block}

# 出力フォーマット

次のキーを持つ JSON オブジェクトを返してください（各値は Markdown 文字列）:
{key_list}

各キーの内容:
- key_finding: 「## 1. 最重要発見」の本文。今月の最大の構造的発見を冒頭で要約し、数値根拠と「だから何をすべきか」を含める。見出しは `###` 以下を使う。
- rankings_note: ランキング表の下に添える短い観察（数行）。表自体は別途コードが描画するので**表は書かない**。
- drilldowns: 「## 3. 個別動画ドリルダウン」の本文。drilldowns 配列の各動画について 流入経路/デモグラ/解釈/次の打ち手 を `###` 見出しで記述。
- patterns: 「## 4. パターン別の発見」。該当するパターン A〜F のみ。
- hypotheses: 「## 5. 今月の仮説カード」。仮説 #1〜#3 を プレイブック6章の形式（観察事実/仮説/打ち手/検証指標と期限）で。
- prior_validation: 「## 6. 先月の仮説検証」。先月レポートがあれば各仮説の結果・学びを、なければ「初回のため対象なし」。
- feature_candidates: 「## 7. 次の機能化候補」。分析中に感じたツール改善案（warnings も参考に）。
- next_month: 「## 8. 来月の検証ポイント」。次月に必ず確認すべき項目。

注意: 各値の中の見出しは `##`（セクション見出し）を含めず、`###` 以下のみ使ってください（セクション見出しはレンダラが付与します）。
"""


def _compact_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Trim heavy per-day timeseries into compact summaries to save tokens."""
    compact = json.loads(json.dumps(bundle))  # deep copy
    for dd in compact.get("drilldowns", []):
        dd["timeseries_views_summary"] = _summarize_series(
            dd.pop("timeseries_views", [])
        )
        dd["timeseries_retention_summary"] = _summarize_series(
            dd.pop("timeseries_retention", [])
        )
    # Subscriber history can be long; keep only first + last few points.
    history = compact.get("subscriber_history", [])
    if len(history) > 12:
        compact["subscriber_history"] = history[:2] + ["…"] + history[-10:]
    return compact


def _summarize_series(points: list[dict[str, Any]]) -> dict[str, Any]:
    """Reduce a per-day series to total / peak / recent-trend signals."""
    if not points:
        return {"available": False}
    values = [p.get("value", 0) for p in points]
    peak = max(points, key=lambda p: p.get("value", 0))
    first7 = sum(values[:7])
    rest = sum(values[7:])
    return {
        "available": True,
        "points": len(points),
        "total": round(sum(values), 1),
        "peak_date": peak.get("date"),
        "peak_value": round(peak.get("value", 0), 1),
        "first7_sum": round(first7, 1),
        "after_day7_sum": round(rest, 1),
        "last_value": round(values[-1], 1),
    }
