#!/usr/bin/env bash
set -euo pipefail

# Send a command to a tmux pane after waiting for shell readiness.
# Dependencies: tmux
# Usage: tmux-send.sh <target> <command> [timeout_seconds]

target="${1:?Usage: tmux-send.sh <target> <command> [timeout_seconds]}"
command_text="${2:?Usage: tmux-send.sh <target> <command> [timeout_seconds]}"
timeout_seconds="${3:-30}"

deadline=$(( $(date +%s) + timeout_seconds ))
while true; do
  pane_content=$(tmux capture-pane -t "$target" -p 2>/dev/null || true)
  if echo "$pane_content" | grep -q '[^[:space:]]'; then
    break
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "tmux-send.sh: timed out waiting for shell readiness on ${target}" >&2
    exit 1
  fi
  sleep 0.5
done

tmux send-keys -l -t "$target" "$command_text"
tmux send-keys -t "$target" Enter
