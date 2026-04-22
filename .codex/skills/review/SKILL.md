---
name: review
description: テスト・レビュー規約に基づいて実装後のコードをレビューする
---

# skill: review

テスト・レビュー規約に基づいて実装後のコードをレビューする。

## 使い方

```
/review <対象機能名 or ファイルパス>
例: /review EventService
例: /review app/core/event_generation.py
```

## レビュー観点

### 1. API 設計
- [ ] レスポンスモデルが Pydantic スキーマで定義されているか
- [ ] エラー時に適切な HTTP ステータスコードと `detail` が返るか
- [ ] 入力バリデーションが行われているか

### 2. ドメインロジック（app/core/）
- [ ] `app/core/` が `httpx` / `sqlalchemy` を import していないか
- [ ] 責務が単一になっているか
- [ ] 型ヒントが全関数に付いているか

### 3. DB 操作
- [ ] セッションが `get_db` 経由か
- [ ] N+1 クエリが発生していないか
- [ ] トランザクション境界が適切か

### 4. 外部 API 連携（app/clients/）
- [ ] タイムアウト設定があるか
- [ ] リトライ処理があるか
- [ ] エラーレスポンスが適切にハンドリングされているか

### 5. テスト
- [ ] 正常系・異常系のテストがあるか
- [ ] 外部依存がモック化されているか

## 出力形式

```
[API] エラー時に detail が空 → 修正必要
[Core] app/core/ が httpx を import している → clients/ に移動
[DB] N+1 クエリの可能性 → joinedload を検討
[Test] 異常系テストなし → 追加必要
```

詳細: `docs/03_standards/test_review_standard.md`
