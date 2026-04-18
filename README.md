# YouTube Analytics

自チャンネルの YouTube 統計を可視化するダッシュボード。Next.js フロントエンドと FastAPI バックエンドで構成し、YouTube Data API v3 / YouTube Analytics API / Google Sheets API からデータを取得する。

## 構成

```
Vercel (Next.js 16, App Router)
        │ HTTPS REST API
Render (FastAPI 0.135)
        ├─ YouTube Data API v3     — 動画メタデータ・チャンネル統計
        ├─ YouTube Analytics API   — 時系列・流入経路・視聴者属性
        └─ Google Sheets API       — 登録者数履歴の保存
```

データベースは使用せず、ほぼすべてのデータは YouTube API から都度取得する。登録者数の推移のみ YouTube API では過去データを取得できないため、Google Sheets に日次で記録する。

## 前提

- Python 3.12+
- Node.js 20+
- Docker / Docker Compose (任意)
- Google Cloud プロジェクトで以下の API を有効化済み
  - YouTube Data API v3
  - YouTube Analytics API
  - Google Sheets API
- YouTube Data API v3 の API キー
- OAuth 2.0 クライアントシークレット (`client_secrets.json`)
- 登録者数履歴を記録する Google スプレッドシート

## 初回セットアップ

```bash
# リポジトリのクローン
git clone <this-repo>
cd youtube-analytics

# バックエンド: 環境変数を設定
cp backend/.env.example backend/.env
# backend/.env を編集:
#   YOUTUBE_API_KEY, CHANNEL_ID, SPREADSHEET_ID,
#   CLIENT_SECRETS_FILE, TOKEN_FILE, FRONTEND_URL

# フロントエンド: 環境変数を設定
cp frontend/.env.local.example frontend/.env.local
# frontend/.env.local を編集:
#   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Google OAuth クライアントシークレットを backend/ に配置
cp /path/to/client_secrets.json backend/client_secrets.json

# OAuth 認証 (token.json が生成される)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup_oauth.py
cd ..

# フロントエンドの依存パッケージをインストール
cd frontend && npm install && cd ..
```

## ローカル起動

### Docker Compose で一括起動

```bash
docker-compose up
```

- バックエンド: http://localhost:8000 (Swagger: http://localhost:8000/docs)
- フロントエンド: http://localhost:3000

### 個別に起動

```bash
# バックエンド (ホットリロード)
cd backend && uvicorn app.main:app --reload

# フロントエンド
cd frontend && npm run dev
```

## デプロイ

### フロントエンド (Vercel)

1. Vercel に GitHub リポジトリを接続し、Root Directory に `frontend` を指定
2. 環境変数 `NEXT_PUBLIC_API_BASE_URL` に Render のバックエンド URL を設定
3. デプロイ

### バックエンド (Render 無料プラン)

1. Render で Web Service を作成、Root Directory に `backend` を指定
2. Build Command: `pip install -r requirements.txt`
3. Start Command: Procfile (`web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`) が適用される
4. 環境変数を設定
   - `YOUTUBE_API_KEY`, `CHANNEL_ID`, `SPREADSHEET_ID`
   - `CLIENT_SECRETS_FILE`, `TOKEN_FILE`
   - `FRONTEND_URL` (Vercel のフロントエンド URL)
5. `client_secrets.json` / `token.json` は Secret Files として配置するか、環境変数経由で注入する
6. 無料プランは無通信時にスリープし、初回アクセス時に約30秒の起動待ちが発生する

## ドキュメント

- [docs/design.md](docs/design.md) — システム構成、技術スタック、デプロイ構成
- [docs/api.md](docs/api.md) — 全 10 エンドポイントの仕様
- [docs/sheets.md](docs/sheets.md) — Google Sheets の構成

## 重要な制約

- **YouTube Analytics API**: 直近 90 日分のデータのみ取得可能
- **YouTube Data API v3 クォータ**: 1 日 10,000 ユニット (1 回のデータ収集で約 200 ユニット)
- **OAuth スコープ**: `youtube.readonly`, `yt-analytics.readonly`, `spreadsheets`
- **秘匿ファイル**: `client_secrets.json`, `token.json`, `.env` はコミット禁止 (`.gitignore` 済み)
