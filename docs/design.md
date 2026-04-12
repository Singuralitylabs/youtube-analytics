# YouTube Analytics System — 基本設計書

## 関連ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [sheets.md](./sheets.md) | Google スプレッドシート構成（登録者数履歴の保存） |
| [api.md](./api.md) | API設計（エンドポイント・レスポンス仕様） |


---

## 1. 概要

### 目的

自分のYouTubeチャンネル（51〜200本）の動画パフォーマンスを継続的に把握し、改善アクションにつなげるため、Webダッシュボードで可視化するシステムを構築する。

### 収集データ

- 基本指標（再生数・高評価数・コメント数）
- 視聴者属性（年齢・性別）
- 時系列推移
- 動画間比較

### 運用方針

| 項目 | 内容 |
|------|------|
| データ取得 | 手動（ダッシュボード上のボタンで随時実行） |
| 対象 | 自分のチャンネルのみ |
| 動画数 | 51〜200本 |
| 出力 | Webダッシュボード（4画面） |
| デプロイ | クラウド（Vercel + Render） |
| 月額費用 | $0 |

---

## 2. データ取得方針

ほとんどのデータは YouTube API から都度取得できるため、データベースは使用しない。
唯一 YouTube が過去の値を提供しない「登録者数の推移」のみ Google スプレッドシートに記録する。

| データ | 取得元 | 保存先 |
|--------|--------|--------|
| 動画一覧・再生数・高評価数・コメント数 | YouTube Data API v3 | 保存しない（都度取得） |
| 動画ごとの日別再生数 | YouTube Analytics API | 保存しない（都度取得） |
| 流入経路・視聴者属性 | YouTube Analytics API | 保存しない（都度取得） |
| **登録者数の推移** | YouTube Data API v3 | **Google スプレッドシートに記録** |

---

## 3. システムアーキテクチャ

```
┌─────────────────────────────────┐
│  Vercel                         │
│  frontend/ (Next.js 16)         │
│  ブラウザ ← SSR/CSR → API呼出   │
└──────────────┬──────────────────┘
               │ HTTPS REST API
┌──────────────▼──────────────────┐
│  Render（無料プラン）            │
│  backend/ (FastAPI)             │
│  ├─ /api/channel/...            │
│  ├─ /api/videos/...             │
│  ├─ /api/rankings               │
│  └─ /api/collect                │
└───┬──────────────────┬──────────┘
    │                  │
    ▼                  ▼
YouTube API      Google Sheets API
（都度取得）     （登録者数履歴の読み書き）
```

---

## 4. 使用 API

| API | 用途 | 認証方式 |
|-----|------|----------|
| YouTube Data API v3 | 動画メタデータ・基本指標 | API Key |
| YouTube Analytics API | 視聴者属性・流入経路・日別再生数 | OAuth 2.0 |
| Google Sheets API | 登録者数履歴の読み書き | OAuth 2.0（同一トークンで兼用） |

### OAuth スコープ

```
https://www.googleapis.com/auth/youtube.readonly
https://www.googleapis.com/auth/yt-analytics.readonly
https://www.googleapis.com/auth/spreadsheets
```

YouTube Analytics API と Google Sheets API は同一の OAuth トークンで認証する。

### クォータ制限

| API | 無料枠 | 本アプリの消費量 |
|-----|--------|----------------|
| YouTube Data API v3 | 10,000ユニット/日 | 約200ユニット/回 |
| YouTube Analytics API | — | 約200ユニット/回 |
| Google Sheets API | 300リクエスト/分 | 数リクエスト/回 |

---

## 5. ディレクトリ構成

```
youtube-analytics/
├── docs/
│   ├── design.md                        # 基本設計書（本ファイル）
│   ├── sheets.md                        # Google スプレッドシート構成
│   └── api.md                           # API設計
│
├── backend/                             # FastAPI アプリケーション
│   ├── app/
│   │   ├── main.py                      # FastAPI インスタンス・ルーター登録・CORS設定
│   │   ├── routers/
│   │   │   ├── channel.py               # GET /api/channel/stats, /timeseries
│   │   │   ├── videos.py                # GET /api/videos, /{id}, /{id}/timeseries 等
│   │   │   ├── rankings.py              # GET /api/rankings
│   │   │   └── collect.py              # POST /api/collect（登録者数をSheetsに記録）
│   │   ├── schemas/
│   │   │   └── responses.py            # Pydantic v2 レスポンス型定義
│   │   └── collectors/
│   │       ├── youtube_data.py         # YouTube Data API v3 クライアント
│   │       ├── youtube_analytics.py   # YouTube Analytics API クライアント
│   │       └── sheets.py              # Google Sheets API クライアント
│   ├── config/
│   │   └── settings.py                 # 環境変数集約（pydantic-settings）
│   ├── scripts/
│   │   └── setup_oauth.py              # OAuth 2.0 初回認証
│   ├── requirements.txt
│   ├── Procfile                        # Render デプロイ用
│   └── .env.example
│
├── frontend/                            # Next.js アプリケーション
│   ├── src/
│   │   ├── app/                         # App Router
│   │   │   ├── layout.tsx              # 共通レイアウト（ナビゲーション）
│   │   │   ├── page.tsx                # / ダッシュボード
│   │   │   ├── rankings/
│   │   │   │   └── page.tsx            # /rankings 動画ランキング
│   │   │   ├── videos/
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx        # /videos/:id 動画詳細
│   │   │   └── compare/
│   │   │       └── page.tsx            # /compare 動画比較
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   └── Sidebar.tsx
│   │   │   ├── charts/
│   │   │   │   ├── LineChart.tsx
│   │   │   │   ├── BarChart.tsx
│   │   │   │   └── PieChart.tsx
│   │   │   └── ui/                     # shadcn/ui コンポーネント
│   │   ├── lib/
│   │   │   └── api.ts                  # バックエンド API クライアント
│   │   └── types/
│   │       └── index.ts                # 共通型定義
│   ├── package.json
│   └── .env.local.example
│
└── docker-compose.yml                  # ローカル開発環境一括起動
```

---

## 6. フロントエンド設計

### 技術スタック

| カテゴリ | ライブラリ | バージョン | 備考 |
|---------|-----------|-----------|------|
| フレームワーク | Next.js (App Router) | 16.x | 最新安定版 |
| 言語 | TypeScript | 6.x | |
| スタイリング | Tailwind CSS | 4.x | v4よりCSSファイル内で `@import "tailwindcss"` を記述する形式に変更 |
| UIコンポーネント | shadcn/ui | latest | Radix UI + Tailwind CSS ベース。ソースをプロジェクトに直接コピーする形式のため自由にカスタマイズ可能 |
| グラフ | Recharts | 3.x | |
| データフェッチ | SWR | 2.x | |

### ページ構成

| URL | ページ名 | 主要コンポーネント |
|-----|---------|------------------|
| `/` | ダッシュボード | KPI カード × 3、登録者数推移グラフ、総再生数グラフ |
| `/rankings` | 動画ランキング | 指標/期間セレクター、ランキングテーブル、棒グラフ |
| `/videos/:id` | 動画詳細 | 指標カード × 4、時系列グラフ、流入経路円グラフ、属性棒グラフ |
| `/compare` | 比較分析 | 動画マルチセレクト、指標セレクト、複数動画重ね折れ線グラフ |

---

## 7. バックエンド設計

### 技術スタック

| カテゴリ | ライブラリ | バージョン | 備考 |
|---------|-----------|-----------|------|
| フレームワーク | FastAPI | 0.135.x | |
| 設定管理 | pydantic-settings | 2.x | |
| スキーマ | Pydantic | v2 | |
| API クライアント | google-api-python-client | 2.x | YouTube API・Sheets API 両方をカバー |
| OAuth 認証 | google-auth-oauthlib | 1.x | |

---

## 8. デプロイ構成

```
[GitHub リポジトリ]
    ├─ frontend/ ─── push ───→ Vercel（自動デプロイ、無料）
    └─ backend/  ─── push ───→ Render（無料 Web Service）
                                    ※ DBなし。Google Sheetsを外部ストレージとして使用
```

### 費用

| サービス | プラン | 月額 |
|---------|--------|------|
| Vercel | Hobby（無料） | $0 |
| Render | 無料 Web Service | $0 |
| Google Sheets | 無料 | $0 |
| YouTube API | 無料枠内 | $0 |
| **合計** | | **$0** |

### 環境変数

**backend（Render の Environment Variables）**

| 変数名 | 説明 |
|--------|------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 の APIキー |
| `CHANNEL_ID` | 分析対象チャンネルID |
| `CLIENT_SECRETS_FILE` | OAuth クライアントシークレットのパス |
| `TOKEN_FILE` | OAuth トークンの保存パス |
| `SPREADSHEET_ID` | 登録者数履歴を記録するスプレッドシートのID |
| `FRONTEND_URL` | CORS 許可先（Vercel のURL） |

**frontend（Vercel の Environment Variables）**

| 変数名 | 説明 |
|--------|------|
| `NEXT_PUBLIC_API_BASE_URL` | バックエンドAPI の URL（RenderのURL） |

### ローカル開発

```
http://localhost:3000      ─ Next.js フロントエンド
http://localhost:8000      ─ FastAPI バックエンド
http://localhost:8000/docs ─ Swagger UI（API確認）
```

---

## 9. セットアップ手順

1. **Google Cloud Project の準備**
   - YouTube Data API v3 を有効化
   - YouTube Analytics API を有効化
   - Google Sheets API を有効化
   - OAuth 2.0 クライアントID 発行（デスクトップアプリ用） → `client_secrets.json` をダウンロード
   - API キー発行

2. **Google スプレッドシートの準備**
   - 新規スプレッドシートを作成
   - URLからスプレッドシートIDを取得し `.env` に設定
   - 詳細は [sheets.md](./sheets.md) を参照

3. **環境変数の設定**
   ```bash
   cp backend/.env.example backend/.env
   # .env を編集: YOUTUBE_API_KEY, CHANNEL_ID, SPREADSHEET_ID を設定
   ```

4. **OAuth 認証（初回のみ）**
   ```bash
   cd backend
   python scripts/setup_oauth.py
   # ブラウザで Google 認証 → token.json が生成される
   ```

5. **依存パッケージのインストール**
   ```bash
   cd backend && pip install -r requirements.txt
   cd frontend && npm install
   ```

6. **起動**
   ```bash
   docker-compose up
   # または個別に:
   cd backend && uvicorn app.main:app --reload
   cd frontend && npm run dev
   ```

---

## 10. 注意事項・制約

| 項目 | 内容 |
|------|------|
| コールドスタート | Render 無料プランはアクセスがないと停止する。初回アクセス時に約30秒の起動待ちが発生する |
| APIクォータ | YouTube Data API v3 は1日10,000ユニット。複数人が頻繁にアクセスする場合は消費量に注意 |
| Analytics制限 | YouTube Analytics API は直近90日分のデータのみ取得可能 |
| セキュリティ | `client_secrets.json`・`token.json`・`.env` は `.gitignore` に追加必須 |
| CORS | バックエンドは `FRONTEND_URL` で指定したオリジンのみ許可 |
