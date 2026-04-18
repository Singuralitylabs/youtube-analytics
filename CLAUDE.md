# CLAUDE.md

このファイルは、リポジトリ内のコードを扱う Claude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクトの現状

現在は**設計フェーズ**です。`docs/` 以下にアーキテクチャドキュメントのみが存在し、バックエンド・フロントエンドのコードはまだ実装されていません。

- `docs/design.md` — システム構成、技術スタック、デプロイ構成、セットアップ手順
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
uvicorn app.main:app --reload   # ホットリロード付き開発サーバー
```

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
| `app/collectors/youtube_analytics.py` | YouTube Analytics API クライアント |
| `app/collectors/sheets.py` | Google Sheets API クライアント |
| `config/settings.py` | 環境変数集約（pydantic-settings） |
| `scripts/setup_oauth.py` | 初回 OAuth 2.0 ブラウザ認証 |

### フロントエンド（`frontend/src/`）

| パス | 役割 |
|------|------|
| `app/page.tsx` | `/` — ダッシュボード（KPI カード・登録者数推移・総再生数グラフ） |
| `app/rankings/page.tsx` | `/rankings` — 指標・期間別の動画ランキング |
| `app/videos/[id]/page.tsx` | `/videos/:id` — 動画詳細（時系列・流入経路・視聴者属性） |
| `app/compare/page.tsx` | `/compare` — 複数動画の指標比較 |
| `components/charts/` | `LineChart.tsx`、`BarChart.tsx`、`PieChart.tsx`（Recharts 3） |
| `lib/api.ts` | バックエンド API クライアント |
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
- **YouTube Data API v3 クォータ**: 1日10,000ユニット。1回のデータ収集で約200ユニット消費
- **OAuth スコープ**: `youtube.readonly`、`yt-analytics.readonly`、`spreadsheets` が必要
- **CORS**: バックエンドは `FRONTEND_URL` で指定したオリジンのみ許可
- **Render 無料プラン**: 無通信が続くとスリープし、初回アクセス時に約30秒の起動待ちが発生
- **要 .gitignore**: `client_secrets.json`、`token.json`、`.env` はコミット禁止

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | Next.js 16（App Router）、TypeScript 6、Tailwind CSS 4、shadcn/ui、Recharts 3、SWR 2 |
| バックエンド | FastAPI 0.135、Pydantic v2、pydantic-settings 2 |
| 外部 API クライアント | google-api-python-client 2、google-auth-oauthlib 1 |
| デプロイ | Vercel（フロントエンド）、Render 無料プラン（バックエンド） |
