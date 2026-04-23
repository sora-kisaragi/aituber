---
name: ship
description: 現在のブランチの変更をコミット → push → PR 作成まで一括で行う
---

# skill: ship

現在のブランチの変更をコミット → push → PR 作成まで一括で行う。

## 使い方

```
/ship <コミットメッセージ>
例: /ship feat: DBスキーマとAlembicマイグレーション実装
```

## 手順

1. 変更ファイルと pre-commit を確認する
   ```bash
   git status
   git diff --stat
   pre-commit run --all-files
   ```

2. ステージングとコミット
   ```bash
   git add <関連ファイル>
   git commit -m "<type>: <概要>"
   ```

3. push する
   ```bash
   git push origin <current-branch>
   ```

4. PR を作成する（関連 Issue があれば `Closes #XX` を含める）
   ```powershell
   @'
   ## 概要
   <変更内容>

   ## 関連 Issue
   Closes #<Issue番号>

   ## 確認事項
   - [ ] 正常系確認
   - [ ] 異常系確認
   - [ ] テスト追加（該当時）
   - [ ] pre-commit 通過
   '@ | gh pr create --title "<type>: <概要>" --body-file -
   ```

## コミットメッセージ規則

| type | 意味 |
|---|---|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメント |
| `refactor` | リファクタリング |
| `chore` | 設定変更 |
| `test` | テスト追加・修正 |

詳細: `docs/05_git/git_strategy.md`
