---
name: new-feature
description: 新しいブランチを main から切って開発を開始する
---

# skill: new-feature

新しいブランチを main から切って開発を開始する。

## 使い方

```
/new-feature <prefix>/<ブランチ名>
例: /new-feature feature/db-schema
例: /new-feature fix/tts-retry
```

## 手順

1. main を最新に更新する
   ```bash
   git checkout main
   git pull origin main
   ```

2. ブランチを作成して移動する
   ```bash
   git checkout -b <prefix>/<ブランチ名>
   # 例: feature/db-schema, fix/tts-retry
   ```

3. ブランチ名・目的をユーザーに確認して開発を開始する

## ブランチ命名規則

| プレフィックス | 用途 | 例 |
|---|---|---|
| `feature/` | 新機能 | `feature/db-schema` |
| `fix/` | バグ修正 | `fix/tts-retry` |
| `docs/` | ドキュメント | `docs/api-reference` |
| `refactor/` | リファクタリング | `refactor/event-service` |
| `chore/` | 設定・依存関係 | `chore/update-deps` |

詳細: [Git 戦略](../../../docs/05_git/git_strategy.md)
