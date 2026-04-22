---
name: update-skill
description: 使用したスキルの実行結果を振り返り、SKILL.md を改善する
---

# skill: update-skill

直前に使用したスキルの実行を振り返り、SKILL.md の改善点を特定して更新する。
スキルは使うたびに育てる。

## 使い方

```
/update-skill <スキル名>
例: /update-skill ship
例: /update-skill review
```

## 手順

1. 対象スキルの SKILL.md を読む
   - Claude Code: `.claude/skills/<name>/SKILL.md`
   - Codex: `.codex/skills/<name>/SKILL.md`

2. 直前の実行を振り返る（以下の観点で）
   - 手順が曖昧で判断に迷った箇所はあったか？
   - 手順が多すぎ / 少なすぎたか？
   - エラーや想定外の動作が起きたか？
   - より簡潔または効果的な方法があったか？
   - コマンド例が古くなっていないか？

3. 改善案をユーザーに提示する（変更前 / 変更後を明示）

4. ユーザーが承認したら両方の SKILL.md を更新する
   - `.claude/skills/<name>/SKILL.md`
   - `.codex/skills/<name>/SKILL.md`
   - Codex の場合は `agents/openai.yaml` の `default_prompt` も確認する

5. 変更内容をコミットする
   ```bash
   git add .claude/skills/<name>/SKILL.md .codex/skills/<name>/SKILL.md
   git commit -m "chore: update <name> skill based on usage feedback"
   ```

## 改善の判断基準

| 状況 | 対応 |
|---|---|
| 手順が曖昧で毎回迷う | 具体例を追加する |
| 手順が長すぎる | 本質でない手順を削除 / 折りたたむ |
| コマンドがエラーになった | 正しいコマンドに修正する |
| 新しいベストプラクティスを発見した | 手順に反映する |
| 使わない手順がある | 削除する |

## 注意

- ユーザーの承認なしに SKILL.md を書き換えない
- 両方（`.claude/` と `.codex/`）を常に同期する
- 変更は必ずコミットして履歴に残す
