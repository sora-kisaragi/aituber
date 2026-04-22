---
name: sync-main
description: main を最新に同期し、現在のブランチをリベースする
---

# skill: sync-main

main を最新に同期し、現在のブランチをリベースする。

## 使い方

```
/sync-main
```

## 手順

1. 現在のブランチを記録する
   ```bash
   git branch --show-current
   ```

2. main を最新に更新する
   ```bash
   git fetch origin
   git checkout main
   git pull origin main
   ```

3. 元のブランチに戻ってリベースする
   ```bash
   git checkout <元のブランチ>
   git rebase main
   ```

4. コンフリクトがあれば内容を確認してユーザーに報告する

## 注意

- リベース後は `git push --force-with-lease` が必要になる場合がある
- コンフリクトが複雑な場合はユーザーに確認してから進める

詳細: `docs/05_git/git_strategy.md`
