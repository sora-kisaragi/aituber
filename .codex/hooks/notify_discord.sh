#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOCAL_ENV_FILE="${SCRIPT_DIR}/.env.local"

# 優先してローカル設定ファイルを読む（Git 管理外）
if [[ -f "${LOCAL_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${LOCAL_ENV_FILE}"
  set +a
fi

# フォールバック: ~/.bashrc の export を読む
if [[ -z "${DISCORD_WEBHOOK_URL:-}" && -f "${HOME}/.bashrc" ]]; then
  DISCORD_WEBHOOK_URL="$(
    sed -n 's/^export DISCORD_WEBHOOK_URL="\([^"]*\)"/\1/p' "${HOME}/.bashrc" \
      | tail -n 1
  )"
  export DISCORD_WEBHOOK_URL
fi

EVENT="${1:-checkpoint}"
TITLE="${2:-Codex Hook}"
BODY="${3:-}"
ISSUE="${4:-}"
BRANCH="${5:-}"
STRICT_MODE="${DISCORD_NOTIFY_STRICT:-1}"
STRICT_ARGS=()
if [[ "${STRICT_MODE}" != "0" ]]; then
  STRICT_ARGS=(--strict)
fi

"${REPO_ROOT}/.venv/bin/python" "${REPO_ROOT}/scripts/codex_hooks/notify_discord.py" \
  --event "${EVENT}" \
  --title "${TITLE}" \
  --body "${BODY}" \
  --issue "${ISSUE}" \
  --branch "${BRANCH}" \
  "${STRICT_ARGS[@]}"
