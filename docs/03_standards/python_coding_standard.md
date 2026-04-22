# Python コーディング規約 — aituber

## 1. 基本方針

- Python 3.11+ を前提とする
- 型ヒントを全関数に付ける（`mypy --strict` レベルを目標）
- コメント・docstring は **日本語** で書く
- フォーマッタ・リンタは `ruff` を使用（pre-commit で自動適用）

---

## 2. 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| クラス | PascalCase | `EventService`, `QwenTTSClient` |
| 関数・メソッド | snake_case | `generate_event`, `synthesize` |
| 変数 | snake_case | `segment_id`, `audio_path` |
| 定数 | UPPER_SNAKE_CASE | `DEFAULT_SEGMENT_DURATION` |
| プライベート | 先頭に `_` | `_build_prompt` |
| モジュール | snake_case | `event_generation.py` |

---

## 3. 型ヒント

```python
# 良い例
def generate(self, segment_id: str) -> list[Event]:
    ...

# 悪い例（型ヒントなし）
def generate(self, segment_id):
    ...
```

- `Optional[X]` の代わりに `X | None` を使う（Python 3.10+）
- `Any` の多用は避ける。使う場合はコメントで理由を記載

---

## 4. 責務分離ルール

| パッケージ | 責務 | 禁止事項 |
|---|---|---|
| `app/core/` | ビジネスロジック | `httpx`, `sqlalchemy` の import |
| `app/clients/` | 外部 API 通信 | DB 操作 |
| `app/api/` | HTTP ルーティング | ビジネスロジック直接実装 |
| `app/models/` | データ定義 | ビジネスロジック |
| `app/db/` | DB セッション管理 | ビジネスロジック |

`app/core/` は外部依存なしで単体テスト可能な状態を保つ。

---

## 5. エラーハンドリング

```python
# 良い例
try:
    response = await client.post(url, json=payload)
    response.raise_for_status()
except httpx.TimeoutException:
    logger.error("TTS API タイムアウト: url=%s", url)
    raise
except httpx.HTTPStatusError as e:
    logger.error("TTS API エラー: status=%d", e.response.status_code)
    raise

# 悪い例（握り潰し）
try:
    response = await client.post(url, json=payload)
except Exception:
    pass
```

- 裸の `except:` は禁止
- エラーは必ず `logger` に記録してから再 raise する
- 外部 API 呼び出しには必ず `timeout` を設定する

---

## 6. ログ

```python
from app.utils.logging import logger

# 使い方
logger.info("セグメント分割開始: video_id=%s", video_id)
logger.debug("VLM レスポンス: %s", response)
logger.error("TTS 生成失敗: segment_id=%s", segment_id, exc_info=True)
```

- `print()` は使わない。`logger.debug()` を使う
- 本番環境で不要な詳細（プロンプト全文等）は `logger.debug()` にする
- 秘匿情報（API キー等）はログに出力しない

---

## 7. 設定値

```python
# 良い例：設定は app/config/config.py 経由
from app.config.config import settings
duration = settings.segment_duration

# 悪い例：ハードコード
duration = 5
```

- マジックナンバーは `settings` または定数化する

---

## 8. コメント・docstring

```python
def plan_for_segment(self, segment_id: str) -> list[UtterancePlan]:
    """指定セグメントのイベントから発話計画を生成する。"""
    # 連続発話抑制: 直前発話から EVENT_GROUPING_WINDOW 秒以内はスキップ
    ...
```

- docstring は公開メソッドに付ける（1 行で済む場合は 1 行）
- コメントは「なぜ」を書く。「何をしているか」はコードから読める

---

## 9. テスト

- テストは `tests/` 配下に `test_<module>.py` で作成
- 外部依存（DB・外部 API）は `pytest-mock` でモック化
- テスト関数名: `test_<対象>_<条件>_<期待結果>`

```python
def test_generate_event_normal_scene_returns_event():
    ...

def test_generate_event_empty_vlm_output_returns_default_event():
    ...
```
