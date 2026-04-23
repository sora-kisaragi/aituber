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

### ファイルヘッダー
- [ ] モジュール docstring（triple quotes）が `import` より前にあるか
- [ ] 目的・関連（Issue番号 / 設計書ID）が記載されているか
- [ ] 作成者・作成日が記載されているか

### 命名規則
- [ ] クラス名が PascalCase か（`EventService`, `QwenTTSClient`）
- [ ] 関数・変数名が snake_case か
- [ ] 定数が UPPER_SNAKE_CASE か
- [ ] プライベートメンバーに `_` プレフィックスがあるか

### 型ヒント
- [ ] 全関数の引数・戻り値に型ヒントがあるか
- [ ] 戻り値なしの関数に `-> None` があるか
- [ ] `Optional[X]` より `X | None` を使っているか（Python 3.10+）
- [ ] 括弧と空白が PEP 8 準拠か（型注釈ありは `= 10`、なしは `=10`）

### 責務分離
- [ ] `app/core/` が `httpx` / `sqlalchemy` を direct import していないか
- [ ] `app/clients/` が DB 操作を行っていないか
- [ ] `app/api/` が直接ビジネスロジックを持っていないか

### コメント・Docstring
- [ ] Docstring が Google スタイルか（Args / Returns / Raises）
- [ ] Docstring に型を重複記載していないか（型ヒントに一本化）
- [ ] コメントが "Why" を書いているか（"What" はコードから読める）
- [ ] `""" """` をコメント目的で使っていないか（`#` を使う）
- [ ] 複数処理段階がある関数に処理単位コメントがあるか

### エラーハンドリング
- [ ] 裸の `except:` がないか
- [ ] 例外を握りつぶしていないか（`logger` 記録 + 再 raise）
- [ ] 外部 API 呼び出しに `timeout` が設定されているか

### ログ
- [ ] `print()` が残っていないか（`logger.debug()` を使う）
- [ ] エラーログに文脈情報（`user_id` 等）が含まれているか
- [ ] 秘匿情報がログに出力されていないか

### テスト（test_*.py のみ）
- [ ] テスト名が `test_functionName_expectedBehavior` 形式か
- [ ] 正常系・異常系の両方があるか
- [ ] Arrange / Act / Assert 構造になっているか
- [ ] 外部依存がモック化されているか

## 出力形式

```
[ヘッダー] モジュール docstring がない → 追加必要
[命名] QwenTtsClient → QwenTTSClient に修正
[型ヒント] synthesize() に -> None がない → 追加必要
[責務] app/core/planning.py が httpx を import → clients/ に移動
[Docstring] fetch_user() に Args: がない → 追加必要
[エラー] except: が裸 → except Exception as e: に修正
[テスト] 異常系テストなし → 追加必要
```

詳細: [コーディング規約](../../../docs/03_standards/python_coding_standard.md)

## 実行後の改善確認（必須）

スキル実行の最後に、次を必ず人間へ確認する。

1. 今回の進め方の感想（良かった点）
2. 使いにくかった点・迷った点（使い勝手）
3. エージェントからの改善提案（手順 / コマンド / 出力）
4. このスキルを今すぐ更新するか（Yes / No）

### 遷移ルール

- Yes: `/update-skill py-review` を実行し、改善案を提示して承認後に反映する
- No: 更新見送り理由を 1 行で記録し、次回見直しの条件を確認する
- 関連 Issue がある場合: 確認結果（更新した / 見送った理由）を Issue コメントで共有する
