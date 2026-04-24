---
name: create-issue
description: GitHub Issue を正しい粒度・構造で登録する
---

# skill: create-issue

GitHub Issue を正しい粒度・構造で登録する。

## 使い方

```
/create-issue
```

## Issue の種別と使い分け

| 種別 | いつ使うか | Label |
|---|---|---|
| **Task Issue** | 実装タスク単位（1〜3 日で完了する粒度） | `phase:mvp / quality / ops` |
| **Bug Issue** | コード上の不具合を発見したとき | `bug` + `priority:S/A/B` |
| **Epic Issue** | 複数 Task をまとめる親 Issue | `epic` + フェーズラベル |

## 登録前レビュー（必須）

`gh issue create` を実行する前に、必ず人間へ次を提示してレビューを受ける。

1. 作成予定タイトル
2. 付与予定ラベル
3. Issue 本文ドラフト（チェックリスト・完了条件を含む）

- 人間の `OK` が出るまで Issue を作成しない
- 修正依頼があれば反映後に再提示し、承認後に作成する

---

## Task Issue テンプレート

```
タイトル: [1-X] <タスク名>

## 親 Issue
#1 MVP実況パイプライン構築

## タスク
- [ ] タスク1
- [ ] タスク2

## 完了条件
<具体的な動作確認方法>
```

---

## Bug Issue テンプレート

```
タイトル: [Bug] <問題の概要>

## 概要
<何が問題か・影響範囲>

## 問題箇所
`<ファイルパス>` L<行番号>

## 再現手順
1. ...

## 期待する動作
...

## 関連
- #XX
```

---

## Labels

| Label | 意味 |
|---|---|
| `epic` | 親 Issue |
| `bug` | 不具合 |
| `phase:mvp` | MVP フェーズ |
| `phase:quality` | 品質改善フェーズ |
| `phase:ops` | 運用フェーズ |
| `priority:S` | 最優先 |
| `priority:A` | 高優先 |
| `priority:B` | 中優先 |

## gh コマンド例

```bash
# Task Issue
gh issue create \
  --title "[1-X] <タイトル>" \
  --body "..." \
  --label "phase:mvp"

# Bug Issue
gh issue create \
  --title "[Bug] <タイトル>" \
  --body "..." \
  --label "bug,priority:S"
```

詳細: [Git 戦略](../../../docs/05_git/git_strategy.md)

## 推奨フロー

1. 既存 Issue を確認して重複を回避する
2. 作成する Issue の粒度を決める（必要なら複数に分割）
3. 作成予定のタイトル・ラベル・本文ドラフトを人間へ提示する
4. 人間のレビュー反映後、`gh issue create` を実行する
5. 作成結果 URL を共有する

## 実行後の改善確認（必須）

スキル実行の最後に、次を必ず人間へ確認する。

1. 今回の進め方の感想（良かった点）
2. 使いにくかった点・迷った点（使い勝手）
3. エージェントからの改善提案（手順 / コマンド / 出力）
4. このスキルを今すぐ更新するか（Yes / No）

### 遷移ルール

- Yes: `/update-skill create-issue` を実行し、改善案を提示して承認後に反映する
- No: 更新見送り理由を 1 行で記録し、次回見直しの条件を確認する
- 関連 Issue がある場合: 確認結果（更新した / 見送った理由）を Issue コメントで共有する
