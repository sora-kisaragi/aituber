---
name: py-review
description: Python コーディング規約に基づいてコードをレビューする
---

# skill: py-review

Python コーディング規約に基づいてコードをレビューする。

## 使い方

```
/py-review <ファイルパス or モジュール名>
例: /py-review app/core/event_generation.py
例: /py-review app/clients/qwen_tts_client.py
```

## チェック項目

### 命名規則
- [ ] クラス名が PascalCase か（`EventService`, `QwenTTSClient`）
- [ ] 関数・変数名が snake_case か
- [ ] 定数が UPPER_SNAKE_CASE か

### 型ヒント
- [ ] 全関数の引数・戻り値に型ヒントがあるか
- [ ] `Optional[X]` より `X | None` を使っているか（Python 3.10+）

### 責務分離
- [ ] `app/core/` が `httpx` / `sqlalchemy` を import していないか
- [ ] `app/clients/` が DB 操作を行っていないか
- [ ] `app/api/` が直接ビジネスロジックを持っていないか

### エラーハンドリング
- [ ] 裸の `except:` がないか
- [ ] 外部 API 呼び出しに timeout が設定されているか
- [ ] エラーが呼び出し元に伝播しているか

### その他
- [ ] `ruff check` でエラーがないか
- [ ] コメントが日本語で書かれているか
- [ ] 不要な `print()` が残っていないか

## 出力形式

```
[命名] QwenTtsClient → QwenTTSClient に修正
[型ヒント] synthesize() の戻り値型がない → 追加必要
[責務] app/core/planning.py が httpx を import → clients/ に移動
[エラー] except: が裸 → except Exception as e: に修正
```

詳細: `docs/03_standards/python_coding_standard.md`
