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
- [ ] クラス名が PascalCase か
- [ ] 関数・変数名が snake_case か
- [ ] 定数が UPPER_SNAKE_CASE か

### 型ヒント
- [ ] 全関数の引数・戻り値に型ヒントがあるか
- [ ] 戻り値なしの関数に `-> None` があるか
- [ ] `Optional[X]` より `X | None` を使っているか
- [ ] 括弧と空白が PEP 8 準拠か

### 責務分離
- [ ] `app/core/` が `httpx` / `sqlalchemy` を import していないか
- [ ] `app/clients/` が DB 操作を行っていないか

### コメント・Docstring
- [ ] Docstring が Google スタイルか（Args / Returns / Raises）
- [ ] Docstring に型を重複記載していないか
- [ ] コメントが "Why" を書いているか
- [ ] `""" """` をコメント目的で使っていないか

### エラーハンドリング
- [ ] 裸の `except:` がないか
- [ ] 例外を握りつぶしていないか
- [ ] 外部 API 呼び出しに `timeout` が設定されているか

### テスト（test_*.py のみ）
- [ ] テスト名が `test_functionName_expectedBehavior` 形式か
- [ ] 正常系・異常系の両方があるか
- [ ] Arrange / Act / Assert 構造になっているか

## 出力形式

```
[ヘッダー] モジュール docstring がない → 追加必要
[命名] QwenTtsClient → QwenTTSClient に修正
[型ヒント] synthesize() に -> None がない → 追加必要
[Docstring] fetch_user() に Args: がない → 追加必要
[エラー] except: が裸 → 修正必要
[テスト] 異常系テストなし → 追加必要
```

詳細: `docs/03_standards/python_coding_standard.md`

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
