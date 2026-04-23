---
name: start
description: 作業開始時に GitHub Issues を確認し、ブランチ作成まで一括実行する
---

# skill: start

新しい作業を始める前に GitHub Issues を確認し、取り掛かる Issue を選んでブランチを切る。

## 使い方

```
/start
```

## 手順

1. Open な Issue 一覧を取得する
   ```bash
   gh issue list --repo sora-kisaragi/aituber --state open --label "phase:mvp"
   ```

2. ラベル・番号を確認して作業候補を提示する

3. ユーザーが取り掛かる Issue を選ぶ

4. 選ばれた Issue の詳細を確認する
   ```bash
   gh issue view <番号> --repo sora-kisaragi/aituber
   ```

5. Issue に応じたブランチを切る
   ```bash
   git checkout main
   git pull origin main
   git checkout -b <prefix>/<issue-slug>
   ```

6. Issue に作業開始コメントを残す
   ```bash
   gh issue comment <番号> --body "作業開始します。ブランチ: \`<ブランチ名>\`"
   ```

## フェーズラベル

| Label | 意味 |
|---|---|
| `phase:mvp` | MVP パイプライン構築（最優先） |
| `phase:quality` | 品質改善フェーズ |
| `phase:ops` | 安定化・運用フェーズ |

詳細: `docs/05_git/git_strategy.md`

## 実行後の改善確認（必須）

スキル実行の最後に、次を必ず人間へ確認する。

1. 今回の進め方の感想（良かった点）
2. 使いにくかった点・迷った点（使い勝手）
3. エージェントからの改善提案（手順 / コマンド / 出力）
4. このスキルを今すぐ更新するか（Yes / No）

### 遷移ルール

- Yes: `/update-skill start` を実行し、改善案を提示して承認後に反映する
- No: 更新見送り理由を 1 行で記録し、次回見直しの条件を確認する
- 関連 Issue がある場合: 確認結果（更新した / 見送った理由）を Issue コメントで共有する
