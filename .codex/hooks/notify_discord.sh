#!/usr/bin/env bash
set -euo pipefail

EVENT="${1:-checkpoint}"
TITLE="${2:-Codex Hook}"
BODY="${3:-}"
ISSUE="${4:-}"
BRANCH="${5:-}"

.venv/bin/python scripts/codex_hooks/notify_discord.py \
  --event "${EVENT}" \
  --title "${TITLE}" \
  --body "${BODY}" \
  --issue "${ISSUE}" \
  --branch "${BRANCH}"
