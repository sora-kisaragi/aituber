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
