# API設計

## 概要

| 項目 | 内容 |
|------|------|
| ベースURL（ローカル） | `http://localhost:8000` |
| ベースURL（本番） | `https://your-api.onrender.com` |
| フォーマット | JSON |
| ドキュメント | `/docs`（Swagger UI、開発時のみ） |

### データ取得方針

| エンドポイント | データ取得元 |
|-------------|------------|
| チャンネル統計・動画一覧・ランキング | YouTube Data API v3（都度取得） |
| 時系列・流入経路・視聴者属性 | YouTube Analytics API（都度取得） |
| 登録者数推移 | Google スプレッドシート |
| データ記録 | Google スプレッドシートへ書き込み |

---

## エンドポイント一覧

| Method | Path | 説明 |
|--------|------|------|
| GET | [`/api/channel/stats`](#get-apichannelstats) | チャンネルの最新統計 |
| GET | [`/api/channel/timeseries`](#get-apichanneltimeseries) | 登録者数・総再生数の推移（Sheetsから取得） |
| GET | [`/api/videos`](#get-apivideos) | 全動画の最新指標一覧 |
| GET | [`/api/videos/{video_id}`](#get-apivideosvideo_id) | 動画詳細サマリー |
| GET | [`/api/videos/{video_id}/timeseries`](#get-apivideosvideo_idtimeseries) | 動画指標の時系列 |
| GET | [`/api/videos/{video_id}/traffic`](#get-apivideosvideo_idtraffic) | 流入経路内訳 |
| GET | [`/api/videos/{video_id}/demographics`](#get-apivideosvideo_iddemographics) | 視聴者属性 |
| GET | [`/api/rankings`](#get-apirankings) | 指標別動画ランキング |
| GET | [`/api/compare`](#get-apicompare) | 複数動画の時系列比較 |
| POST | [`/api/collect`](#post-apicollect) | 登録者数をスプレッドシートに記録 |

---

## エンドポイント詳細

### GET `/api/channel/stats`

YouTube Data API v3 からチャンネルの最新統計を取得して返す。

**レスポンス**
```json
{
  "channel_id": "UCxxxxxxxxxx",
  "subscriber_count": 12000,
  "total_view_count": 980000,
  "video_count": 87
}
```

---

### GET `/api/channel/timeseries`

Google スプレッドシートから登録者数・総再生数の履歴を取得して返す。

**クエリパラメータ**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `metric` | string | `subscriber_count` | `subscriber_count` / `total_view_count` |

**レスポンス**
```json
[
  { "collected_at": "2026-03-01 10:00:00", "value": 11200 },
  { "collected_at": "2026-03-15 09:30:00", "value": 11500 },
  { "collected_at": "2026-04-11 14:30:00", "value": 12000 }
]
```

---

### GET `/api/videos`

YouTube Data API v3 から全動画の最新指標を取得して返す。

**レスポンス**
```json
[
  {
    "video_id": "xxxxxxxxxx",
    "title": "動画タイトル",
    "published_at": "2024-01-15",
    "view_count": 45000,
    "like_count": 1200,
    "comment_count": 87
  }
]
```

---

### GET `/api/videos/{video_id}`

YouTube Data API v3 から指定動画の詳細を取得して返す。

**パスパラメータ**

| パラメータ | 説明 |
|-----------|------|
| `video_id` | YouTube 動画ID |

**レスポンス**
```json
{
  "video_id": "xxxxxxxxxx",
  "title": "動画タイトル",
  "published_at": "2024-01-15",
  "duration_sec": 720,
  "view_count": 45000,
  "like_count": 1200,
  "comment_count": 87
}
```

---

### GET `/api/videos/{video_id}/timeseries`

YouTube Analytics API から指定動画の日別指標を取得して返す。

**クエリパラメータ**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `metric` | string | `views` | `views` / `estimatedMinutesWatched` / `averageViewDuration` / `averageViewPercentage` |
| `days` | integer | `30` | 直近何日分を取得するか（最大90） |

**レスポンス**
```json
[
  { "date": "2026-03-12", "value": 320 },
  { "date": "2026-03-13", "value": 410 },
  { "date": "2026-03-14", "value": 280 }
]
```

---

### GET `/api/videos/{video_id}/traffic`

YouTube Analytics API から指定動画の流入経路内訳を取得して返す。

**クエリパラメータ**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `days` | integer | `30` | 集計対象の直近日数 |

**レスポンス**
```json
[
  { "traffic_source_type": "YT_SEARCH", "views": 18000 },
  { "traffic_source_type": "SUGGESTED_VIDEOS", "views": 15000 },
  { "traffic_source_type": "EXT_URL", "views": 5000 }
]
```

---

### GET `/api/videos/{video_id}/demographics`

YouTube Analytics API から指定動画の視聴者属性を取得して返す。

**クエリパラメータ**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `days` | integer | `30` | 集計対象の直近日数 |

**レスポンス**
```json
[
  { "age_group": "age18-24", "gender": "male",   "view_percentage": 28.5 },
  { "age_group": "age18-24", "gender": "female",  "view_percentage": 12.3 },
  { "age_group": "age25-34", "gender": "male",   "view_percentage": 22.1 }
]
```

---

### GET `/api/rankings`

YouTube Analytics API から指定期間の動画ランキングを取得して返す。

**クエリパラメータ**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `metric` | string | `views` | `views` / `estimatedMinutesWatched` / `averageViewPercentage` |
| `limit` | integer | `20` | 返す件数（最大50） |
| `days` | integer | `30` | 集計対象の直近日数 |

**レスポンス**
```json
[
  {
    "rank": 1,
    "video_id": "xxxxxxxxxx",
    "title": "動画タイトル A",
    "published_at": "2024-01-15",
    "value": 45000
  },
  {
    "rank": 2,
    "video_id": "yyyyyyyyyy",
    "title": "動画タイトル B",
    "published_at": "2024-03-20",
    "value": 38000
  }
]
```

---

### GET `/api/compare`

YouTube Analytics API から複数動画の日別指標を取得して返す。

**クエリパラメータ**

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `ids` | string | — | 動画IDをカンマ区切りで指定（例: `id1,id2,id3`） |
| `metric` | string | `views` | 取得する指標 |
| `days` | integer | `30` | 直近何日分を取得するか |

**レスポンス**
```json
[
  { "video_id": "xxxxxxxxxx", "title": "動画 A", "date": "2026-03-12", "value": 320 },
  { "video_id": "yyyyyyyyyy", "title": "動画 B", "date": "2026-03-12", "value": 150 },
  { "video_id": "xxxxxxxxxx", "title": "動画 A", "date": "2026-03-13", "value": 410 },
  { "video_id": "yyyyyyyyyy", "title": "動画 B", "date": "2026-03-13", "value": 180 }
]
```

---

### POST `/api/collect`

YouTube Data API v3 から現在の登録者数・総再生数を取得し、Google スプレッドシートに1行追記する。

**リクエストボディ**: なし

**レスポンス**
```json
{
  "status": "ok",
  "collected_at": "2026-04-11 14:30:00",
  "subscriber_count": 12000,
  "total_view_count": 980000
}
```

---

## エラーレスポンス

| ステータスコード | 説明 |
|----------------|------|
| `400 Bad Request` | クエリパラメータが不正（例: 無効な `metric` 値） |
| `404 Not Found` | 指定した `video_id` が存在しない |
| `429 Too Many Requests` | YouTube API のクォータ上限に達した |
| `500 Internal Server Error` | YouTube API 障害・Sheets API 障害 |

**エラーレスポンス形式**
```json
{
  "detail": "video_id 'xxxxxxxxxx' が見つかりません"
}
```
