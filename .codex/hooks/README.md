# Codex Hooks

Git hooks ではなく、Codex 作業フローから明示的に呼び出す通知フック。

## 事前設定

```bash
# 推奨: ローカル専用設定（Git 管理外）
cat > .codex/hooks/.env.local <<'EOF'
DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
EOF
chmod 600 .codex/hooks/.env.local

# 代替: 環境変数
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
chmod +x .codex/hooks/notify_discord.sh
```

`notify_discord.sh` は次の順序で webhook URL を解決する:
1. `.codex/hooks/.env.local`
2. 環境変数 `DISCORD_WEBHOOK_URL`
3. `~/.bashrc` の `export DISCORD_WEBHOOK_URL=...`

デフォルトで strict モード（送信失敗時に非0終了）で動作する。
失敗を無視したい場合のみ `DISCORD_NOTIFY_STRICT=0` を設定する。

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
