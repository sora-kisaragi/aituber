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

0. 作業ツリーの汚れを確認する
   ```bash
   git status --short
   ```
   - 対象 Issue と無関係な変更がある場合は、そのまま `push/PR` しない
   - dirty の場合は次のどれかで整理する
     - 推奨: 一時 worktree で隔離して進める（元の汚れは触らない）
     ```bash
     git worktree add /tmp/<repo>-ship main
     cd /tmp/<repo>-ship
     git checkout -b <prefix>/<issue-slug>-pr
     git cherry-pick <対象コミット>
     ```
     - 同じ作業ツリーを使う必要がある場合: 変更を一時退避する
      ```bash
      git stash push -u -m "wip-before-ship"
      # ship 完了後
      git stash pop
      ```
     - 改行差分だけを疑う場合: まず確認する
      ```bash
      git diff --ignore-cr-at-eol --stat
      ```
   - 変更破棄（`git restore` など）はユーザー確認なしで実行しない

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

5. マージと後処理
   ```bash
   gh pr merge <PR番号> --merge --delete-branch
   git checkout main
   git pull origin main
   git branch -d <作業ブランチ> || true
   if git ls-remote --exit-code --heads origin <作業ブランチ> >/dev/null 2>&1; then
     git push origin --delete <作業ブランチ>
   fi
   git worktree remove --force /tmp/<repo>-ship
   ```

- 方針: PR マージ後は、不要になったブランチを削除して `main` に戻した状態を作業の終了条件にする

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

## 実行後の改善確認（必須）

スキル実行の最後に、次を必ず人間へ確認する。

1. 今回の進め方の感想（良かった点）
2. 使いにくかった点・迷った点（使い勝手）
3. エージェントからの改善提案（手順 / コマンド / 出力）
4. このスキルを今すぐ更新するか（Yes / No）

### 遷移ルール

- Yes: `/update-skill ship` を実行し、改善案を提示して承認後に反映する
- No: 更新見送り理由を 1 行で記録し、次回見直しの条件を確認する
- 関連 Issue がある場合: 確認結果（更新した / 見送った理由）を Issue コメントで共有する
