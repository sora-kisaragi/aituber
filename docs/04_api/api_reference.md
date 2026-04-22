# API リファレンス — aituber

## ベース URL

```
http://localhost:8000
```

---

## エンドポイント一覧

### 動画管理

| メソッド | パス | 概要 |
|---|---|---|
| `POST` | `/videos` | 動画をアップロードして登録 |
| `GET` | `/videos/{video_id}` | 動画メタ情報・処理状況を取得 |
| `POST` | `/videos/{video_id}/compose` | 音声・字幕を動画に合成して出力 |

### イベント生成

| メソッド | パス | 概要 |
|---|---|---|
| `POST` | `/events/generate` | 動画のセグメント全体にイベント生成を実行 |

### 発話計画

| メソッド | パス | 概要 |
|---|---|---|
| `POST` | `/plans/generate` | イベントをグループ化し発話計画を生成 |

### 実況生成

| メソッド | パス | 概要 |
|---|---|---|
| `POST` | `/commentaries/generate` | LLM に発話計画を送り実況文を生成 |

### 音声合成

| メソッド | パス | 概要 |
|---|---|---|
| `POST` | `/tts/generate` | Qwen TTS API に音声合成リクエストを送信 |

### 字幕生成

| メソッド | パス | 概要 |
|---|---|---|
| `POST` | `/subtitles/generate` | 音声長ベースで SRT 字幕ファイルを生成 |

---

## 詳細仕様

### POST /videos

**リクエスト**
- `Content-Type: multipart/form-data`
- `file`: MP4 動画ファイル

**レスポンス**
```json
{
  "video_id": "uuid"
}
```

---

### POST /events/generate

**リクエスト**
```json
{
  "video_id": "uuid"
}
```

**レスポンス**
```json
[
  {
    "event_id": "uuid",
    "segment_id": "uuid",
    "type": "kill",
    "timestamp": 12.4,
    "importance": 0.8,
    "details": {}
  }
]
```

---

### POST /tts/generate

**リクエスト**
```json
{
  "commentary_id": "uuid",
  "tts_mode": "custom_voice",
  "speaker": "ono_anna",
  "language": "japanese",
  "instruct": ""
}
```

**レスポンス**
```json
{
  "audio_id": "uuid",
  "storage_path": "/var/aituber/media/audio/xxx.wav",
  "duration_seconds": 2.4
}
```

---

## エラーレスポンス

```json
{
  "detail": "エラーの説明（日本語）"
}
```

| ステータス | 意味 |
|---|---|
| `400` | バリデーションエラー |
| `404` | リソースが見つからない |
| `500` | サーバー内部エラー |
| `503` | 外部 API（TTS / LLM）障害 |
