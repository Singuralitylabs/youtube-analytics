# CLAUDE.md

このファイルは、リポジトリ内のコードを扱う Claude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクトの現状

**現行の主機能は「月次レポートの自動生成」**です。毎月、直近90日の分析＋対策レポートを自動生成して `reports/YYYY-MM.md` にコミットし、Slack に通知します（GitHub Actions）。

- **フロントエンド（`frontend/`）は開発凍結中**（コードは残存。手を入れない）。
- **バックエンド（`backend/`）は実装済み**。FastAPI の HTTP 層（routers）は現状維持しつつ、レポート生成（`backend/app/report/`）が collector 群を直接 import して再利用する。
- レポート生成は **ハイブリッド**: 数値は Python が API から確定集計し、解釈・対策は Gemini API（無料枠）が執筆する。

ドキュメント:
- `docs/monthly-report.md` — **月次レポート自動生成のパイプライン・セットアップ・実行（最初に読む）**
- `docs/analysis-playbook.md` — レポートが従う分析方法論
- `docs/design.md` — 凍結中の Web アプリ構成の設計
- `docs/api.md` — 全10エンドポイントのリクエスト・レスポンス仕様
- `docs/sheets.md` — 登録者数履歴を保存する Google Sheets の構成

---

## 開発コマンド

### 初回セットアップ

```bash
# 1. 環境変数の設定
cp backend/.env.example backend/.env
# .env を編集: YOUTUBE_API_KEY, CHANNEL_ID, SPREADSHEET_ID, CLIENT_SECRETS_FILE, TOKEN_FILE, FRONTEND_URL

cp frontend/.env.local.example frontend/.env.local
# .env.local を編集: NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# 2. OAuth 認証（token.json が生成される）
cd backend && python scripts/setup_oauth.py

# 3. 依存パッケージのインストール
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

### ローカル起動

```bash
# Docker で両サービスを一括起動
docker-compose up

# または個別に起動:
cd backend && uvicorn app.main:app --reload   # http://localhost:8000
cd frontend && npm run dev                    # http://localhost:3000
# Swagger UI: http://localhost:8000/docs
```

### フロントエンド

```bash
cd frontend
npm run dev      # 開発サーバー
npm run build    # 本番ビルド
npm run lint     # ESLint
```

### バックエンド

```bash
cd backend
uvicorn app.main:app --reload   # ホットリロード付き開発サーバー（凍結中のフロント用 API）
```

### 月次レポート生成（現行の主機能）

```bash
cd backend
# データ/描画のみ確認（Gemini 呼び出しなし・退避先へ出力）
python scripts/generate_monthly_report.py --month 2026-05 --out /tmp/reports --dry-run --skip-author
# 解釈・対策まで生成（要 GEMINI_API_KEY）
python scripts/generate_monthly_report.py --month 2026-05 --out /tmp/reports --dry-run
```

詳細・セットアップは `docs/monthly-report.md`。自動実行は `.github/workflows/monthly-report.yml`（毎月1日、前月分）。

---

## アーキテクチャ

```
Vercel（Next.js 16、App Router）
        │ HTTPS REST API
Render（FastAPI 0.135）
        ├─ YouTube Data API v3    （API Key 認証）       — 動画メタデータ・チャンネル統計
        ├─ YouTube Analytics API  （OAuth 2.0）          — 時系列・流入経路・視聴者属性
        └─ Google Sheets API      （OAuth 2.0、同一トークン） — 登録者数履歴の読み書き
```

**データベースなし。** ほぼすべてのデータは YouTube API から都度取得する。唯一の例外が「登録者数の推移」で、YouTube API が過去データを提供しないため Google Sheets に記録する。

### バックエンド（`backend/`）

| パス | 役割 |
|------|------|
| `app/main.py` | FastAPI インスタンス・ルーター登録・CORS 設定 |
| `app/routers/` | `channel.py`、`videos.py`、`rankings.py`、`collect.py` |
| `app/schemas/responses.py` | Pydantic v2 レスポンス型定義 |
| `app/collectors/youtube_data.py` | YouTube Data API v3 クライアント |
| `app/collectors/youtube_analytics.py` | YouTube Analytics API クライアント（`top_videos` で多指標を1クエリ取得） |
| `app/collectors/sheets.py` | Google Sheets API クライアント |
| `app/report/builder.py` | 月次レポートの確定データ集計（collector を直接 import） |
| `app/report/author.py` | Gemini API で解釈・対策セクションを執筆（`response_json_schema` で8キーJSONを強制） |
| `app/report/renderer.py` | 確定表＋LLM 文章を結合し Markdown を組み立て・書き出し |
| `app/report/slack.py` | Slack Webhook へ要約＋GitHub URL を通知 |
| `config/settings.py` | 環境変数集約（pydantic-settings。`GEMINI_*`/`SLACK_WEBHOOK_URL`/`REPORT_OUTPUT_DIR`/`GITHUB_*` を追加） |
| `scripts/setup_oauth.py` | 初回 OAuth 2.0 ブラウザ認証 |
| `scripts/generate_monthly_report.py` | 月次レポート生成 CLI（builder→author→renderer→Slack） |

### フロントエンド（`frontend/src/`）

| パス | 役割 |
|------|------|
| `app/globals.css` | デザイントークン（CSS 変数 + `@theme inline`）。フォント変数・配色・`ga-card`/`chip`/`ticker` 等の共通クラス |
| `app/layout.tsx` | 共通レイアウト（Sidebar + TopBar + main）。`next/font` で Manrope / IBM Plex Mono を読み込み |
| `app/page.tsx` | `/` — ダッシュボード（KPI カード × 3・期間セグメント・登録者数/総再生数推移・Top5動画・データ収集ボタン） |
| `app/rankings/page.tsx` | `/rankings` — 指標ピル × 期間セグメント・表彰台 × 3・リーダーボードテーブル |
| `app/videos/[id]/page.tsx` | `/videos/:id` — ヒーロー＋4統計・時系列パネル・流入経路・視聴者属性 |
| `app/compare/page.tsx` | `/compare` — 動画ピッカー（最大 8）・選択チップ・重ね折れ線・期間内合計 |
| `components/layout/Sidebar.tsx` | 左ナビ（Reports セクションのみ） |
| `components/layout/TopBar.tsx` | 上部 sticky バー（パンくず・最終収集日チップ） |
| `components/charts/LineChart.tsx` | グラデーション領域付き折れ線（Recharts 3） |
| `components/charts/BarChart.tsx` | 縦/横棒（rainbow オプションで多色化） |
| `components/charts/PieChart.tsx` | ドーナツ + サイド凡例 |
| `components/charts/Sparkline.tsx` | KPI カード内の小型推移描画（area / bars） |
| `components/charts/shared.tsx` | 共通 `ChartTooltip` と `CHART_COLORS` パレット |
| `components/ui/KpiCard.tsx` | KPI カード（数値・デルタチップ・スパークライン・ホバーグロー） |
| `components/ui/Panel.tsx` | `ga-card` レイアウト共通コンテナ（eyebrow/title/actions スロット） |
| `components/ui/PageHeader.tsx` | ページ見出し |
| `components/ui/SegmentedControl.tsx` | 期間など択一選択 |
| `components/ui/EmptyState.tsx` | データ無し表示 |
| `components/ui/{button,input,select,table,card,badge}.tsx` | shadcn/ui ベース。トークンに合わせて再調整 |
| `lib/api.ts` | バックエンド API クライアント |
| `lib/utils.ts` | `cn` / `formatNumber` / `formatCompact` / `pctDelta` / `formatShortDate` 等 |
| `types/index.ts` | 共通型定義 |

### API エンドポイント一覧

| Method | パス | データ取得元 |
|--------|------|-------------|
| GET | `/api/channel/stats` | YouTube Data API v3 |
| GET | `/api/channel/timeseries` | Google Sheets |
| GET | `/api/videos` | YouTube Data API v3 |
| GET | `/api/videos/{id}` | YouTube Data API v3 |
| GET | `/api/videos/{id}/timeseries` | YouTube Analytics API |
| GET | `/api/videos/{id}/traffic` | YouTube Analytics API |
| GET | `/api/videos/{id}/demographics` | YouTube Analytics API |
| GET | `/api/rankings` | YouTube Analytics API |
| GET | `/api/compare` | YouTube Analytics API |
| POST | `/api/collect` | Google Sheets へ書き込み |

---

## Git 運用ルール

コミットを実行する前に、**必ずユーザーに確認を取ること**。

---

## 重要な制約事項

- **YouTube Analytics API**: 直近90日分のデータのみ取得可能
- **`averageViewPercentage` / `averageViewDuration` は `dimensions=video` のソートキーにできない**（API が 400/500）。維持率は `top_videos` で `views` ソートの追加カラムとして取得する
- **YouTube Data API v3 クォータ**: 1日10,000ユニット。1回のデータ収集で約200ユニット消費
- **OAuth スコープ**: `youtube.readonly`、`yt-analytics.readonly`、`spreadsheets` が必要
- **OAuth 同意画面は「本番」公開必須**: Testing のままだと refresh token が7日で失効し、月次自動実行が壊れる
- **リポジトリは private**: 月次レポート（`reports/`）にチャンネルの非公開データを含むため。`reports/` は private 前提で **追跡対象**（`docs/` は設計書専用）
- **Slack 通知にレポートの GitHub URL を載せる**ため、ワークフローはレポートをコミット後に通知する
- **Gemini 無料枠を使用**（コスト $0、`gemini-2.5-flash`）。⚠️ 無料枠は送信内容が学習に使われ得るため、機密重視なら有料課金へ切替
- **CORS**: バックエンドは `FRONTEND_URL` で指定したオリジンのみ許可（凍結中フロント用）
- **Render 無料プラン**: 無通信が続くとスリープし、初回アクセス時に約30秒の起動待ちが発生
- **要 .gitignore**: `client_secrets.json`、`token.json`、`.env` はコミット禁止

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Next.js 16（App Router）、TypeScript 6、Tailwind CSS 4、shadcn/ui、Recharts 3、SWR 2 |
| バックエンド | FastAPI 0.135、Pydantic v2、pydantic-settings 2 |
| 外部 API クライアント | google-api-python-client 2、google-auth-oauthlib 1 |
| 月次レポート生成 | google-genai（Gemini API・無料枠）、GitHub Actions（月次 cron）、Slack Incoming Webhook |
| デプロイ | Render 無料プラン（バックエンド）。フロントエンドは凍結中で未デプロイ（Vercel 連携は廃止） |
