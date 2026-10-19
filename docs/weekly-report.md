# 週次レポート自動生成

毎週、直前に終わった ISO 週（月曜〜日曜・JST）の **軽量な変化＋翌週の打ち手レポート** を自動生成し、`reports/weekly/YYYY-Www.md` にコミットして Slack に要約を通知する仕組み。月次レポート（[`monthly-report.md`](./monthly-report.md)）を置き換えず、早いサイクルの補助として併用する。

分析方法論は [`analysis-playbook.md`](./analysis-playbook.md) に従う。週次ではサンプルが小さくノイズになりやすい「パターン別発見」「ドリルダウン」「機能化候補」は省く。

---

## パイプライン

```
GitHub Actions（週次 cron / 手動 workflow_dispatch）
  └─ backend/scripts/generate_weekly_report.py
       ├─ app/report/builder.py    build_weekly_bundle（当週/前週・WoW・順位変動・新規初動）
       ├─ app/report/author.py     Gemini API が最重要ポイント・来週アクション・先週検証を執筆
       ├─ app/report/renderer.py   確定表＋LLM 文章を結合 → reports/weekly/YYYY-Www.md
       └─（ワークフローが git commit & push）
  └─ app/report/slack.py  Webhook へ要約＋GitHub URL を通知（コミット後）
```

**ハイブリッド生成**は月次と同じ。数値は Python、解釈・対策は Gemini（`response_json_schema` で週次3キーの JSON を強制）。Gemini / YouTube / Sheets の一時障害は共通リトライ（指数バックオフ＋ジッター）で吸収し、最終失敗時は月次と同じ「数値のみ」フォールバック。

### データソース対応

| レポートのセクション | データ源 | 生成 |
|---|---|---|
| 0. 週次スナップショット（前週比） | Data API＋Sheets（履歴）＋ Analytics `channel_totals` | コード |
| 2. 当週ランキング Top5（再生/視聴時間・順位変動） | Analytics `top_videos`（当週・前週の2期間） | コード |
| 3. 新規公開動画の初動 | Data API（公開日）＋ Analytics（当週指標） | コード |
| 1. 最重要ポイント / 4. 来週のアクション / 5. 先週検証 | 確定データ＋プレイブック＋直近の週次レポート | Gemini API |

---

## 週の区切りと実行タイミング

| 項目 | 方針 |
|---|---|
| 週の区切り | 月曜〜日曜、JST（ISO 週）。ラベルは `YYYY-Www`（例: `2026-W41`） |
| 対象週 | 実行時点で直前に終わった週。`--week` / workflow 入力で指定可 |
| 比較 | 前週比（WoW）。再生数が少ない週は率を出さず絶対値のみ |
| 定期実行 | 毎週月曜 00:00 UTC（= 09:00 JST） |
| 月初スキップ | **schedule かつ UTC 日付が1日**のとき週次をスキップ（月次と同日衝突回避）。`workflow_dispatch` はスキップしない |
| 前週レポート参照 | スキップで欠番があっても、存在する直近の週次ファイルを参照（暦上の前週で WoW 数値は計算） |

### タイムゾーン制約（Analytics / 公開時刻）

- **レポートの週ラベル・対象週**は JST の ISO 週（月〜日）。
- **YouTube Analytics API** の `startDate` / `endDate` は **Pacific Time（America/Los_Angeles）** で解釈される。実装では JST 週の `[月 00:00, 日 23:59:59]` を PT カレンダー日へ変換してからクエリする（`app.report.weeks.jst_range_to_analytics_dates`）。日付粒度のため、週境界付近では PT 側に数時間ぶんのはみ出しがあり得る。
- **新規公開の当週判定**は Data API の `publishedAt`（UTC 瞬間）を JST 日付に変換してから行う（UTC 日付の切り出しでは境界を誤る）。

---

## セットアップ

月次と同じ Secrets / OAuth / private リポジトリ要件を流用する。追加の Secret は不要。詳細は [`monthly-report.md`](./monthly-report.md) のセットアップ節を参照。

---

## 実行

### 自動（GitHub Actions）

`.github/workflows/weekly-report.yml` が毎週月曜 00:00 UTC に起動し、直前週を対象に生成→コミット→Slack 通知する。手動実行は Actions タブ → *Weekly Analytics Report* → *Run workflow*（`week` 入力で対象週を指定可能、空欄なら直前週）。

### ローカル

```bash
cd backend
pip install -r requirements.txt

# プレビュー（Slack/コミットせず、退避先に出力。Gemini 呼び出しあり）
python scripts/generate_weekly_report.py --week 2026-W41 --out /tmp/weekly --dry-run

# データ/描画だけ確認（Gemini 呼び出しをスキップ）
python scripts/generate_weekly_report.py --week 2026-W41 --out /tmp/weekly --dry-run --skip-author

# 本番ディレクトリへ生成し、ただちに Slack 通知（ローカル一括）
python scripts/generate_weekly_report.py --week 2026-W41 --notify
```

| フラグ | 挙動 |
|---|---|
| （なし） | 生成＋ファイル書き出し＋Slack state 保存（Slack 投稿はしない） |
| `--dry-run` | 生成のみ（state を書かず、Slack も投稿しない） |
| `--skip-author` | Gemini 呼び出しをスキップし、確定データ＋表のみ生成 |
| `--notify` | 生成後ただちに Slack 通知 |
| `--notify-only` | 生成せず、保存済み state から Slack 通知（CI のコミット後ステップ用） |
| `--week YYYY-Www` | 対象週（既定: 直前に終わった ISO 週・JST） |
| `--out PATH` | 出力ディレクトリ（既定: `<repo>/reports/weekly`） |

---

## 堅牢性

- API / Gemini の一時障害は `app/report/retry.py` でリトライ（Gemini: 最大4回・5s→15s→45s、API: 最大3回・短いバックオフ）。ステータスコード優先＋単語境界マッチ（`5000` 等の誤検知を避ける）。
- リトライ後も Gemini が失敗した場合は数値のみで継続し、レポート末尾と Slack に劣化を明示する。Analytics 取得失敗も警告付きで空データ継続（ジョブ全体は落とさない）。
- コミット前に `git pull --rebase` し、月次などとの近接 push 競合を緩和する。

## 検証チェックリスト

- [ ] `cd backend && python -m unittest discover -s tests -v`
- [ ] ローカル: `--dry-run --skip-author` で表・メタ（`analytics_*` PT 日付）を確認
- [ ] ローカル: Gemini あり `--dry-run`（任意）
- [ ] Actions: `workflow_dispatch` で実 API＋Slack を一度流す
- [ ] 月初月曜の schedule がスキップされることを該当日に確認

## 関連

- [`monthly-report.md`](./monthly-report.md) — 月次レポート（同じ Secrets・ハイブリッド方式）
- [`analysis-playbook.md`](./analysis-playbook.md) — 分析方法論・仮説カード書式
