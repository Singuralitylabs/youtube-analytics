# 月次レポート自動生成

毎月、直近90日の **分析結果＋対策（打ち手）レポート** を自動生成し、`reports/YYYY-MM.md` にコミットして Slack に要約を通知する仕組み。手動で画面を見る代わりに、[`analysis-playbook.md`](./analysis-playbook.md) の月次サイクルをコードと Gemini（無料枠）で自動化したもの。

> この方針転換に伴い、**フロントエンド（`frontend/`）の開発は凍結**しています（コードは残存）。バックエンドの collector 群はレポート生成で再利用しています。

---

## パイプライン

```
GitHub Actions（月次 cron / 手動 workflow_dispatch）
  └─ backend/scripts/generate_monthly_report.py
       ├─ app/report/builder.py    収集＋集計（collector を直接 import、数値を確定）
       ├─ app/report/author.py     Gemini API が解釈・対策・仮説カードを執筆
       ├─ app/report/renderer.py   確定表＋LLM 文章を結合 → reports/YYYY-MM.md
       └─（ワークフローが git commit & push）
  └─ app/report/slack.py  Webhook へ要約＋GitHub URL を通知（コミット後）
```

**ハイブリッド生成**: スナップショット・ランキング表・分割マトリクスなどの数値は `builder.py` が API から正確に集計し、`renderer.py` が確定値として表に描画する。解釈を要する「最重要発見 / ドリルダウン / パターン / 仮説カード（対策）/ 前月検証 / 来月の検証」は `author.py` が Gemini API で執筆する（`response_json_schema` で8キーの JSON を強制）。数値の正確さと解釈の質を両立させる狙い。

### データソース対応

| レポートのセクション | データ源 | 生成 |
|---|---|---|
| 0. スナップショット（前月比） | Data API（stats）＋ Sheets（履歴） | コード |
| 2. ランキング（views / 視聴時間 / 維持率 / 食い違い） | Analytics API `top_videos`（多指標1クエリ） | コード |
| 1. 最重要発見 / 3. ドリルダウン / 4. パターン / 5. 仮説カード / 6. 前月検証 / 7. 機能化候補 / 8. 来月 | 上記の確定データ＋プレイブック＋前月レポート | Gemini API |

> 注: `averageViewPercentage` / `averageViewDuration` を `dimensions=video` の **ソートキー** にすると API が 400/500 を返すため、維持率は `views` でソートした多指標クエリの **追加カラム** として取得している（`youtube_analytics_client.top_videos`）。

---

## セットアップ（ユーザー作業）

### 1. リポジトリを private 化 ⚠️

レポートには登録者数・動画パフォーマンス・戦略といった **チャンネルの非公開データ** が含まれる。GitHub URL を Slack に載せるためレポートをコミットするので、**リポジトリを必ず private にすること**（GitHub → Settings → Danger Zone → Change visibility）。`reports/` は private 前提で追跡対象にしている（`docs/` は設計書専用。`.gitignore` のコメント参照）。

### 2. OAuth 同意画面を「本番（In production）」に公開 ⚠️

Google Cloud Console → OAuth consent screen を **Testing のままにしない**。Testing だと **refresh token が 7 日で失効** し、月次自動実行が必ず壊れる。本番公開すれば refresh token は継続有効になる。失効した場合は `python scripts/setup_oauth.py` を再実行してトークンを作り直す。

### 3. GitHub Secrets を登録

リポジトリ Settings → Secrets and variables → Actions → New repository secret:

| Secret 名 | 内容 |
|---|---|
| `GOOGLE_TOKEN_JSON` | `backend/token.json` の中身全文（refresh_token を含む） |
| `GOOGLE_CLIENT_SECRETS_JSON` | `backend/client_secrets.json` の中身全文 |
| `YOUTUBE_API_KEY` | YouTube Data API v3 の API キー |
| `CHANNEL_ID` | 対象チャンネル ID（UC…） |
| `SPREADSHEET_ID` | 登録者数履歴スプレッドシートの ID |
| `GEMINI_API_KEY` | Gemini API キー（[Google AI Studio](https://aistudio.google.com/apikey) で無料発行） |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |

（任意）モデルを変えたい場合は Variables に `GEMINI_MODEL` を設定（既定 `gemini-2.5-flash`。高品質を求めるなら `gemini-2.5-pro` 等）。

> **無料枠について**: `gemini-2.5-flash` は Google AI Studio の無料枠で利用でき、月1回のジョブなら無料枠のレート制限内に十分収まる（コスト $0）。⚠️ ただし**無料枠では送信内容が Google のモデル改善に利用される可能性**がある。レポートにはチャンネルの非公開データが含まれるため、機密性を重視する場合は有料（Pay-as-you-go）課金に切り替える（有料利用ではデータは学習に使われない）。

### 4. Actions の書き込み権限を有効化

Settings → Actions → General → Workflow permissions → **Read and write permissions** を選択（レポートのコミット/プッシュに必要）。

### 5. （推奨）登録者数の定期収集

前月比とパターンF（登録転換）には Sheets 履歴が必要。`POST /api/collect` を定期実行して履歴を蓄積しておくと、スナップショットの前月比が算出される。履歴が無い場合でもレポートは生成され、前月比は「未算出」と表示される。

---

## 実行

### 自動（GitHub Actions）

`.github/workflows/monthly-report.yml` が毎月 1 日 00:00 UTC（09:00 JST）に起動し、**前月**を対象に生成→コミット→Slack 通知する。手動実行は Actions タブ → *Monthly Analytics Report* → *Run workflow*（`month` 入力で対象月を指定可能、空欄なら前月）。

### ローカル

```bash
cd backend
pip install -r requirements.txt

# プレビュー（Slack/コミットせず、退避先に出力。Gemini 呼び出しあり）
python scripts/generate_monthly_report.py --month 2026-05 --out /tmp/reports --dry-run

# データ/描画だけ確認（Gemini 呼び出しをスキップ）
python scripts/generate_monthly_report.py --month 2026-05 --out /tmp/reports --dry-run --skip-author

# 本番ディレクトリへ生成し、ただちに Slack 通知（ローカル一括）
python scripts/generate_monthly_report.py --month 2026-05 --notify
```

| フラグ | 挙動 |
|---|---|
| （なし） | 生成＋ファイル書き出し＋Slack state 保存（Slack 投稿はしない） |
| `--dry-run` | 生成のみ（state を書かず、Slack も投稿しない） |
| `--skip-author` | Gemini 呼び出しをスキップし、確定データ＋表のみ生成 |
| `--notify` | 生成後ただちに Slack 通知 |
| `--notify-only` | 生成せず、保存済み state から Slack 通知（CI のコミット後ステップ用） |
| `--month YYYY-MM` | 対象月（既定: 当月） |
| `--out PATH` | 出力ディレクトリ（既定: `<repo>/reports`） |

---

## 堅牢性

各 API 呼び出しは個別に握りつぶし、失敗してもレポートは生成を継続する（該当箇所は空欄/欠損になり、末尾「データ取得メモ」に警告を記載）。OAuth トークンの失効（`invalid_grant`）や Sheets 権限不足（403）でもクラッシュせず、API キーで取れるスナップショット等は出力される。

## 関連

- [`analysis-playbook.md`](./analysis-playbook.md) — レポートが従う分析方法論（KPIツリー・月次サイクル・パターンA〜F・仮説カード書式・アンチパターン）
- [`api.md`](./api.md) — collector が叩く各 API の仕様
- [`sheets.md`](./sheets.md) — 登録者数履歴の保存形式
