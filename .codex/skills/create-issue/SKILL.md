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

## Issue の種別

| 種別 | Label |
|---|---|
| Task Issue | `phase:mvp / quality / ops` |
| Bug Issue | `bug` + `priority:S/A/B` |
| Epic Issue | `epic` + フェーズラベル |

## Task Issue テンプレート

```bash
gh issue create \
  --title "[1-X] <タスク名>" \
  --body "## 親 Issue
#1

## タスク
- [ ] タスク1
- [ ] タスク2

## 完了条件
<動作確認方法>" \
  --label "phase:mvp"
```

## Bug Issue テンプレート

```bash
gh issue create \
  --title "[Bug] <概要>" \
  --body "## 概要
<影響範囲>

## 問題箇所
\`<ファイルパス>\` L<行番号>

## 再現手順
1.

## 関連
- #XX" \
  --label "bug,priority:S"
```

詳細: `docs/05_git/git_strategy.md`
