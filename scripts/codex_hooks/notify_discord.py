#!/usr/bin/env python3
"""Codex Hook から Discord Webhook 通知を送信するCLI。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime


def parse_args() -> argparse.Namespace:
    """CLI 引数を解析する。

    Args:
        なし。

    Returns:
        通知パラメータを保持した名前空間。
    """
    parser = argparse.ArgumentParser(description="Codex hook 用 Discord 通知")
    parser.add_argument(
        "--event",
        required=True,
        choices=["start", "checkpoint", "blocked", "done", "error"],
        help="通知イベント種別",
    )
    parser.add_argument("--title", required=True, help="通知タイトル")
    parser.add_argument("--body", default="", help="通知本文")
    parser.add_argument("--issue", default="", help="Issue 番号（例: 21）")
    parser.add_argument("--branch", default="", help="ブランチ名（省略時は現在ブランチ）")
    parser.add_argument("--strict", action="store_true", help="通知失敗時に非0で終了")
    return parser.parse_args()


def current_branch() -> str:
    """現在の Git ブランチ名を取得する。

    Args:
        なし。

    Returns:
        ブランチ名。取得失敗時は空文字。
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def build_payload(
    event: str,
    title: str,
    body: str,
    issue: str,
    branch: str,
) -> dict[str, str]:
    """Discord 投稿用 payload を構築する。

    Args:
        event: 通知イベント種別。
        title: 通知タイトル。
        body: 通知本文。
        issue: 関連 Issue 番号。
        branch: 関連ブランチ名。

    Returns:
        Discord Webhook の `content` を含む辞書。
    """
    emoji_map = {
        "start": "🚀",
        "checkpoint": "📍",
        "blocked": "⚠️",
        "done": "✅",
        "error": "❌",
    }
    branch_value = branch or current_branch() or "(unknown)"
    issue_line = f"Issue: #{issue}" if issue else "Issue: (none)"
    lines = [
        f"{emoji_map.get(event, 'ℹ️')} **{title}**",
        f"Event: `{event}`",
        f"Branch: `{branch_value}`",
        issue_line,
        f"Time: {datetime.now(tz=UTC).isoformat()}",
    ]
    if body:
        lines.append("")
        lines.append(body)
    return {"content": "\n".join(lines)}


def send_discord(webhook_url: str, payload: dict[str, str]) -> None:
    """Discord Webhook へ通知を送信する。

    Args:
        webhook_url: 送信先 Discord Webhook URL。
        payload: 投稿内容。

    Returns:
        なし。成功時は副作用として通知を送信する。
    """
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "aituber-codex-hook/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        if response.status >= 300:
            raise RuntimeError(f"Discord webhook failed: HTTP {response.status}")


def main() -> int:
    """通知CLIのメイン処理を実行する。

    Args:
        なし。

    Returns:
        終了コード（0: 成功または非strictスキップ, 1: strict失敗）。
    """
    args = parse_args()
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        print("DISCORD_WEBHOOK_URL が未設定のため通知をスキップします。", file=sys.stderr)
        return 1 if args.strict else 0

    payload = build_payload(
        event=args.event,
        title=args.title,
        body=args.body,
        issue=args.issue,
        branch=args.branch,
    )

    try:
        send_discord(webhook, payload)
    except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as e:
        print(f"Discord 通知失敗: {e}", file=sys.stderr)
        return 1 if args.strict else 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
