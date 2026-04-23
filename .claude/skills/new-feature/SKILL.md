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

## 実行後の改善確認（必須）

スキル実行の最後に、次を必ず人間へ確認する。

1. 今回の進め方の感想（良かった点）
2. 使いにくかった点・迷った点（使い勝手）
3. エージェントからの改善提案（手順 / コマンド / 出力）
4. このスキルを今すぐ更新するか（Yes / No）

### 遷移ルール

- Yes: `/update-skill new-feature` を実行し、改善案を提示して承認後に反映する
- No: 更新見送り理由を 1 行で記録し、次回見直しの条件を確認する
- 関連 Issue がある場合: 確認結果（更新した / 見送った理由）を Issue コメントで共有する
