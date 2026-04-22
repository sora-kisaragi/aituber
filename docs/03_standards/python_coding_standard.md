# Python コーディング規約 — aituber

**Version:** 1.2
**作成日:** 2025-12-25
**最終更新:** 2026-02-17
**作成者:** 宗廣 颯真
**対象:** Python による開発全般（Web / バッチ / スクリプト）

## このページが扱う内容

このページでは **Python におけるコードの書き方（コーディング規約）** のみを扱う。
レビュー手順、環境構築、AI レビュー活用、運用ルールなどは別ページで取り扱う。

含まれる情報: コードスタイル / 命名規則 / 型ヒント / クラス・関数の設計方針 /
コメント・Docstring / エラーハンドリング / ログ / セキュリティ / テスト / 禁止事項 / pyproject.toml 設定

---

## 設計書との整合性

- コードと設計書は常に相互参照可能（双方向）であること
- 設計書に登場する用語・機能名・概念名をモジュール名 / クラス名 / 関数名へ反映する
- 設計変更が入った場合、コードと設計書の差分を放置しない（差分が出るならチケット化する）

---

## コーディング時の基本ルール

- スタイル統一のため Linter（ruff）を使用
- コード整形のため black を使用（`line-length = 120`）
- import 整形に ruff を使用
- 型品質向上のため mypy を推奨（`strict = true`）

---

## ディレクトリ構造

```
aituber/
  ├─ app/
  │   ├─ api/           # REST API ルーター（HTTP のみ）
  │   ├─ core/          # ドメインロジック（外部依存禁止）
  │   ├─ models/        # SQLAlchemy モデル + Pydantic スキーマ
  │   ├─ clients/       # 外部 API クライアント（LLM / TTS）
  │   ├─ db/            # DB セッション・Alembic 設定
  │   ├─ config/        # pydantic-settings による設定読み込み
  │   └─ utils/         # ログ・ファイル操作ユーティリティ
  ├─ tests/
  ├─ pyproject.toml
  └─ .env.example
```

---

## Python ファイルのヘッダー

### 目的

ファイルの責務・背景・設計書との対応をソース先頭だけで把握できるようにする。

### 適用範囲

- `app/` 配下のアプリコード（特に core・api・clients）
- `tests/` は任意（必要性がある場合のみ）
- 自動生成コードは対象外

### テンプレート（推奨）

```python
"""
<ファイルの概要を1行で>（例：実況生成サービスの実装）

- 目的: <このファイルの責務 / 何を提供するか>
- 対象: <主な利用者（例：API層 / バッチ / CLI）>
- 関連: <設計書ID / チケットID / Issue番号など>

作成者: 宗廣 颯真
作成日: YYYY-MM-DD
最終更新者: 宗廣 颯真
最終更新日: YYYY-MM-DD
"""
```

### 記入例

```python
"""
実況生成サービスの実装。

- 目的: 発話計画を受け取り LLM に送信して実況テキストを生成する
- 対象: api/commentaries.py
- 関連: Issue #9, docs/02_design/system_design.md

作成者: 宗廣 颯真
作成日: 2026-04-22
最終更新者: 宗廣 颯真
最終更新日: 2026-04-22
"""
```

---

## コードスタイル

- インデント: スペース 4（タブ禁止）
- 行の長さ: 120 文字以内（black / ruff で統一）
- 文字コード: UTF-8
- import の順序: 標準ライブラリ → サードパーティ → アプリ内部

---

## 命名規則

| 対象 | 規則 | 例 |
|---|---|---|
| 変数 | snake_case | `user_name`, `segment_id` |
| 関数・メソッド | snake_case | `fetch_user`, `generate_event` |
| クラス | PascalCase | `EventService`, `QwenTTSClient` |
| 定数 | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT`, `MAX_RETRY` |
| ファイル名 | snake_case | `event_generation.py` |
| プライベート | 先頭に `_` | `_build_prompt` |

---

## 型ヒント

### すべての関数に型を明記する

```python
def fetch_user(user_id: int) -> User:
    ...

def update_last_login(user_id: int) -> None:
    ...
```

### Union は `|` 記法（Python 3.10+）

```python
def load(data: str | None) -> str:
    ...
```

- `Optional[X]` の代わりに `X | None` を使う
- `Any` の多用は避ける。使う場合はコメントで理由を記載

### 括弧と空白の規則（PEP 8）

```python
# 良い例
def fetch_user(user_id: int) -> User:
    ...
fetch_user(user_id=1)

# NG: 関数名と ( の間に空白
def fetch_user (user_id: int) -> User:

# NG: ( の直後 / ) の直前に空白
f( x, y )

# 型注釈あり: = の前後に空白
def f(limit: int = 10) -> None: ...

# 型注釈なし: = の前後に空白なし
def f(limit=10): ...

# キーワード引数: = の前後に空白なし
fetch_user(user_id=1, include_profile=True)
```

---

## クラスと関数の設計

- 関数の責務は「単一」にする
- ネスト（if / for）は 3 段以内
- 複雑な処理は private メソッドに分離
- 過度な抽象化は禁止（必要以上のクラス化・共通化を避ける）

### 責務分離ルール（aituber 固有）

| パッケージ | 責務 | 禁止事項 |
|---|---|---|
| `app/core/` | ビジネスロジック | `httpx`, `sqlalchemy` の import |
| `app/clients/` | 外部 API 通信 | DB 操作 |
| `app/api/` | HTTP ルーティング | ビジネスロジック直接実装 |
| `app/models/` | データ定義 | ビジネスロジック |
| `app/db/` | DB セッション管理 | ビジネスロジック |

`app/core/` は外部依存なしで単体テスト可能な状態を保つ。

---

## コメントと Docstring

### 基本方針

- コメントは "What（何をしているか）" ではなく "Why（なぜそうするか）" を書く
- 処理単位の説明コメントを適切に挿入し、読み手が処理の塊を追えるようにする
- Docstring は Sphinx による設計書生成を前提に **Google スタイル**で統一する

### 処理単位コメントの規則

1 つの関数内で複数の処理段階がある場合、処理ブロックの前に処理単位コメントを記載する。

```python
def create_user_profile(user_input: dict) -> User:
    # 入力検証（欠損・型・業務ルール）
    ...

    # 既存ユーザー重複チェック
    ...

    # 永続化（リポジトリへ保存）
    ...

    # 応答モデル組み立て
    ...
```

### 行コメントの使い分け

- `""" ... """` は Docstring 用途に限定し、コメント目的では使用しない
- コメントは原則「対象コードの直前」に書く（行末コメントは最小限）

```python
# NG: Docstring をコメント目的で使う
def f() -> None:
    """
    これはコメントのつもり（NG）
    """
    ...

# OK: lint 抑止など例外的な行末コメント
payload: dict[str, Any] = load_payload()  # noqa: ANN401（外部I/FのためAnyを許容）
```

### Docstring 形式（Google スタイル）

```python
def fetch_user(user_id: int) -> User:
    """ユーザーIDを指定してユーザー情報を取得する。

    Args:
        user_id: 対象ユーザーID。正の整数であること。

    Returns:
        ユーザーエンティティ。

    Raises:
        UserNotFound: 指定したIDのユーザーが存在しない場合。
        ValueError: user_id が正の整数でない場合。
    """
    ...
```

- 1行目：80文字以内で何をするかを簡潔に記述
- 型は型ヒントに一本化し、Docstring に重複記載しない
- `dict[str, Any]` 等で型が抽象的な場合は期待するキー・構造を記載する
- セクション順序: `Args:` → `Returns:` → `Raises:` → `Examples:`

---

## エラーハンドリング

### 禁止

- 空の `except:`
- `except Exception:` の乱用
- ログを書かずに例外を無視する行為

### 推奨

```python
try:
    user = repo.get(id)
except UserNotFound:
    logger.warning("User not found", user_id=id)
    raise
```

```python
# 外部 API 呼び出し（必ず timeout 設定）
try:
    response = await client.post(url, json=payload, timeout=10.0)
    response.raise_for_status()
except httpx.TimeoutException:
    logger.error("TTS API タイムアウト: url=%s", url)
    raise
except httpx.HTTPStatusError as e:
    logger.error("TTS API エラー: status=%d", e.response.status_code)
    raise
```

---

## ログ出力

- JSON 形式を推奨
- `user_id` / `trace_id` など文脈情報を含める
- `print` デバッグは禁止。`logging` または `structlog` を使用

```python
from app.utils.logging import logger

logger.info("セグメント分割開始: video_id=%s", video_id)
logger.debug("VLM レスポンス: %s", response)
logger.error("TTS 生成失敗: segment_id=%s", segment_id, exc_info=True)
```

---

## セキュリティ

- `eval` / `exec` 禁止
- Secrets（API キー / パスワード等）の直書き禁止（`.env` 経由で管理）
- `requests` / `httpx` は `timeout` を必須設定
- SQL は ORM または安全なプレースホルダを使用

---

## テスト

### 命名規則

```
test_functionName_expectedBehavior
```

規約に従い `camelCase` の関数名部分を維持する（アンダースコア区切りではなく）:

```python
def test_fetchUser_returns_user_when_exists():
    ...

def test_fetchUser_raises_UserNotFound_when_missing():
    ...

def test_generateEvent_returns_default_when_vlm_empty():
    ...
```

### 基本方針

- 正常系・異常系を両方作成する
- Mock は必要最低限で使用する
- 外部依存（DB・外部 API）は `pytest-mock` でモック化する
- テストは `tests/` 配下に `test_<module>.py` で作成する

### pytest 設定

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v"
```

### conftest.py の活用

共通フィクスチャは `tests/conftest.py` に集約する。

```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    client.complete.return_value = "実況テキストのサンプル"
    return client

@pytest.fixture
def mock_tts_client():
    client = MagicMock()
    client.synthesize.return_value = ("/var/media/audio.wav", 2.4)
    return client
```

### テストの構造（Arrange / Act / Assert）

```python
def test_generateEvent_returns_event_when_normal_scene(mock_vision_service):
    # Arrange（準備）
    service = EventService(vision=mock_vision_service)
    mock_vision_service.analyze_frame.return_value = {
        "scene_summary": "戦闘中",
        "objects": ["敵", "プレイヤー"],
        "confidence": 0.8,
    }

    # Act（実行）
    events = service.generate(segment_id="seg-001")

    # Assert（検証）
    assert len(events) >= 1
    assert events[0].speak_recommended is True
```

---

## 禁止事項

- 未使用変数・未使用 import
- マジックナンバー
- `print` デバッグ
- コメントとコードの不一致
- 例外の握りつぶし
- 過度な if-else ネスト
- グローバル変数の乱用

---

## サンプルコード（規約適用例）

```python
"""
実況生成サービスの実装。

- 目的: 発話計画を受け取り LLM に送信して実況テキストを生成する
- 対象: api/commentaries.py
- 関連: Issue #9

作成者: 宗廣 颯真
作成日: 2026-04-22
最終更新者: 宗廣 颯真
最終更新日: 2026-04-22
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UtterancePlan:
    plan_id: str
    event_summary: str
    style: str


class LLMClientError(Exception):
    pass


def generate_commentary(plan: UtterancePlan, llm_client) -> str:
    """発話計画をもとに実況テキストを生成する。

    Args:
        plan: 発話計画。event_summary と style を含む。
        llm_client: LLM API クライアント。

    Returns:
        生成された実況テキスト（1〜2文）。

    Raises:
        LLMClientError: LLM API の呼び出しに失敗した場合。
    """

    # プロンプト構築（スタイルに応じたシステム指示を含める）
    prompt = _build_prompt(plan)

    # LLM 呼び出し
    try:
        text = llm_client.complete(prompt)
    except Exception as e:
        logger.error("LLM 呼び出し失敗: plan_id=%s", plan.plan_id, exc_info=True)
        raise LLMClientError("LLM 呼び出しに失敗しました") from e

    # 返却（1〜2文に収まるか検証）
    return text.strip()


def _build_prompt(plan: UtterancePlan) -> str:
    """発話計画からLLM向けプロンプトを構築する。"""
    return f"スタイル: {plan.style}\nイベント: {plan.event_summary}\n1〜2文で実況してください。"
```

---

## 付録：pyproject.toml 設定例

```toml
[tool.black]
line-length = 120

[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]

[tool.isort]
profile = "black"

[tool.mypy]
ignore_missing_imports = true
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v"
```
