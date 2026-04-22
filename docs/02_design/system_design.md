# システム設計書 — aituber MVP

## 1. アーキテクチャ概要

```
mp4 入力
   ↓ POST /videos
VideoIngestService
   ↓ videos テーブル
SegmentationService（FFmpeg）
   ↓ segments / frames テーブル
VisionService（VLM / ダミー）
   ↓
EventService
   ↓ events テーブル
UtterancePlanner
   ↓ utterance_plans テーブル
CommentaryService（LLM）
   ↓ commentaries テーブル
QwenTTSClient
   ↓ audios テーブル
SubtitleService
   ↓ subtitles テーブル
Composer（FFmpeg）
   ↓
mp4 出力
```

---

## 2. データモデル

### videos

| カラム | 型 | 説明 |
|---|---|---|
| `id` | UUID | PK |
| `title` | TEXT | 動画タイトル |
| `duration_seconds` | FLOAT | 動画長（秒） |
| `fps` | FLOAT | フレームレート |
| `storage_path` | TEXT | ローカルファイルパス |
| `metadata` | JSONB | その他メタデータ |
| `created_at` | TIMESTAMP | 登録日時 |

### segments

| カラム | 型 | 説明 |
|---|---|---|
| `id` | UUID | PK |
| `video_id` | UUID | FK → videos |
| `start_time` | FLOAT | 開始時刻（秒） |
| `end_time` | FLOAT | 終了時刻（秒） |
| `type` | TEXT | `intro` / `gameplay` 等 |

### frames

| カラム | 型 | 説明 |
|---|---|---|
| `id` | UUID | PK |
| `segment_id` | UUID | FK → segments |
| `timestamp` | FLOAT | フレーム時刻（秒） |
| `image_path` | TEXT | 画像ファイルパス |
| `features` | JSONB | 物体検出結果・OCR 値 |

### events

| カラム | 型 | 説明 |
|---|---|---|
| `id` | UUID | PK |
| `segment_id` | UUID | FK → segments |
| `timestamp` | FLOAT | イベント発生時刻 |
| `type` | TEXT | `kill` / `score_change` 等 |
| `importance` | FLOAT | 重要度（0〜1） |
| `details` | JSONB | ゲーム固有の詳細情報 |

### utterance_plans

| カラム | 型 | 説明 |
|---|---|---|
| `id` | UUID | PK |
| `video_id` | UUID | FK → videos |
| `event_ids` | JSONB | 関連イベント ID リスト |
| `start_time` | FLOAT | 発話開始予定時刻 |
| `end_time` | FLOAT | 発話終了予定時刻 |
| `priority` | INT | 優先度 |
| `style` | TEXT | `excited` / `calm` 等 |

### commentaries

| カラム | 型 | 説明 |
|---|---|---|
| `id` | UUID | PK |
| `utterance_plan_id` | UUID | FK → utterance_plans |
| `language` | TEXT | `japanese` 等 |
| `style` | TEXT | 実況スタイル |
| `text` | TEXT | 生成された実況文 |
| `llm_raw_response` | JSONB | LLM の生レスポンス |

### audios

| カラム | 型 | 説明 |
|---|---|---|
| `id` | UUID | PK |
| `commentary_id` | UUID | FK → commentaries |
| `tts_mode` | TEXT | `custom_voice` 等 |
| `speaker` | TEXT | 話者名 |
| `language` | TEXT | 言語 |
| `storage_path` | TEXT | WAV ファイルパス |
| `duration_seconds` | FLOAT | 音声長（秒） |

### subtitles

| カラム | 型 | 説明 |
|---|---|---|
| `id` | UUID | PK |
| `commentary_id` | UUID | FK → commentaries |
| `file_path` | TEXT | SRT ファイルパス |
| `start_time` | FLOAT | 字幕開始時刻 |
| `end_time` | FLOAT | 字幕終了時刻 |

---

## 3. クラス責務

| クラス | モジュール | 主なメソッド |
|---|---|---|
| `SegmentationService` | `app/core/segmentation.py` | `execute(video_id)` |
| `VisionService` | `app/core/vision.py` | `analyze_frame(frame_id)` |
| `EventService` | `app/core/event_generation.py` | `generate(segment_id)` |
| `UtterancePlanner` | `app/core/planning.py` | `plan_for_segment(segment_id)` |
| `PromptGenerator` | `app/core/prompt.py` | `build_prompt(plan)` |
| `CommentaryService` | `app/core/prompt.py` | `generate(plan)` |
| `QwenTTSClient` | `app/clients/qwen_tts_client.py` | `synthesize(text, mode, speaker, language, instruct)` |
| `LLMClient` | `app/clients/llm_client.py` | `complete(messages)` |
| `SubtitleService` | `app/core/subtitle.py` | `generate(commentary_id)` |
| `Composer` | `app/core/composer.py` | `compose(video_id)` |

---

## 4. 設計方針

### 責務分離
- `app/core/` は純粋なビジネスロジック。ファイル I/O・外部 API 呼び出しは禁止
- `app/clients/` は外部 API の呼び出しとレスポンスパースのみ
- テスト時は `app/clients/` をモックに差し替え可能にする

### セグメント基準処理
- すべての処理はセグメント単位に分割可能にする
- 失敗したセグメントのみ再処理できる設計にする

### JSONB 活用
- ゲームごとに異なる属性（`events.details`、`frames.features`）は JSONB に保存
- GiST インデックスで検索性を確保
