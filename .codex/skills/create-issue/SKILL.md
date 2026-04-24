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

## 登録前レビュー（必須）

`gh issue create` を実行する前に、必ず人間へ次を提示してレビューを受ける。

1. 作成予定タイトル
2. 付与予定ラベル
3. Issue 本文ドラフト（チェックリスト・完了条件を含む）

- 人間の `OK` が出るまで Issue を作成しない
- 修正依頼があれば反映後に再提示し、承認後に作成する

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
