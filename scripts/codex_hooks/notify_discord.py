#!/usr/bin/env python3
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
