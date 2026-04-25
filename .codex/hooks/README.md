# Codex Hooks

Git hooks ではなく、Codex 作業フローから明示的に呼び出す通知フック。

## 事前設定

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
chmod +x .codex/hooks/notify_discord.sh
```

## 使い方

```bash
.codex/hooks/notify_discord.sh start "long-run 開始" "Issue #21 パフォーマンス検証"
.codex/hooks/notify_discord.sh checkpoint "中間報告" "計測完了・分析中" 21
.codex/hooks/notify_discord.sh blocked "要対応" "外部API待ちで停止" 21
.codex/hooks/notify_discord.sh done "完了" "PR作成まで完了" 21
```

引数:
- 第1引数: event (`start` / `checkpoint` / `blocked` / `done` / `error`)
- 第2引数: title
- 第3引数: body（任意）
- 第4引数: issue 番号（任意）
- 第5引数: branch 名（任意）
