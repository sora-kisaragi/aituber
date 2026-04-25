---
name: long-run
description: 長時間作業を中断せず、自走専用ブランチで継続し最後に main へ統合する
---

# skill: long-run

長時間の実装・調査タスクを、不要な確認待ちを挟まずに継続実行する。
作業は `main` 直下で行わず、自走専用ブランチを親にして進める。

## 使い方

```
/long-run <作業内容>
例: /long-run #21 パフォーマンス検証を最後まで進める
```

## 実行前提

- このスキルは Full Access 前提で実行する
- 明示的な停止指示があるまで、実装・検証・修正を継続する
- マイルストーンごとに進捗は共有するが、「続けてよいか」の確認は原則しない
- 判断が必要な箇所は、影響が小さい側に倒して前進する

## ブランチ運用（必須）

1. `main` から自走専用の親ブランチを作る
   ```bash
   git checkout main
   git pull origin main
   git checkout -b autopilot/<topic>
   ```
2. 各実装は親ブランチから子ブランチを切って進める
   ```bash
   git checkout autopilot/<topic>
   git checkout -b feature/<task-slug>
   ```
3. 子ブランチで実装・検証後、親ブランチへマージする
   ```bash
   git checkout autopilot/<topic>
   git merge --no-ff feature/<task-slug>
   ```
4. すべて完了したら `autopilot/<topic>` から `main` へ PR を作る
5. `main` への最終 PR まで、作業途中の子ブランチは `main` に直接 PR しない

## 実行手順

0. 目的と完了条件を 1〜3 行で再確認する
1. 自走専用親ブランチ `autopilot/<topic>` を用意する
2. 影響範囲を調査し、子ブランチを切って最短で価値が出る順に実装する
3. 実装したら `.venv/bin/pre-commit run --all-files` と必要テストを実行する
4. 失敗時は自己修正して再実行し、通るまで繰り返す
5. 子ブランチを親へ順次マージし、最後に親ブランチから `main` へ PR を作成する
6. 完了条件を満たしたら結果・未解決事項・次の推奨アクションを報告する

## デフォルト前提

- Python 系コマンドは `.venv/bin/...` を使う
- 変更は最小差分で行い、不要なリファクタは混ぜない
- 関連テストを優先し、必要に応じて `tests/test_core` など範囲を広げる

## Codex Hooks（Discord 通知）

- Git hooks ではなく Codex hooks として通知を送る
- `DISCORD_WEBHOOK_URL` を設定し、以下を実行する
  ```bash
  .venv/bin/python scripts/codex_hooks/notify_discord.py \
    --event start --title "long-run 開始" --body "<作業内容>"
  ```
- 推奨イベント:
  - `start`: 作業開始
  - `checkpoint`: 中間マイルストーン
  - `blocked`: ブロック発生
  - `done`: 完了

## ブロック時の動き

- 10 分以上進捗が止まる場合は、代替案で前進できる道を先に試す
- 必要なら `blocked` イベントを Discord に送信する
- それでも解消しない場合のみ、質問は 1 回・短文で行う

## 実行後の改善確認（必須）

スキル実行の最後に、次を必ず人間へ確認する。

1. 今回の進め方の感想（良かった点）
2. 使いにくかった点・迷った点（使い勝手）
3. エージェントからの改善提案（手順 / コマンド / 出力）
4. このスキルを今すぐ更新するか（Yes / No）

### 遷移ルール

- Yes: `/update-skill long-run` を実行し、改善案を提示して承認後に反映する
- No: 更新見送り理由を 1 行で記録し、次回見直しの条件を確認する
- 関連 Issue がある場合: 確認結果（更新した / 見送った理由）を Issue コメントで共有する
