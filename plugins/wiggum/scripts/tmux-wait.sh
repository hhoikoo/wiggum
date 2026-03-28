#!/usr/bin/env bash
set -euo pipefail

# Poll tmux pane for a grep pattern in the last N lines.
# Dependencies: tmux
# Usage: tmux-wait.sh <target> <pattern> [timeout_seconds] [lines]

target="${1:?Usage: tmux-wait.sh <target> <pattern> [timeout_seconds] [lines]}"
pattern="${2:?Usage: tmux-wait.sh <target> <pattern> [timeout_seconds] [lines]}"
timeout_seconds="${3:-30}"
lines="${4:-10}"

deadline=$(( $(date +%s) + timeout_seconds ))
while true; do
  if tmux capture-pane -t "$target" -p -S "-${lines}" 2>/dev/null | grep -q "$pattern"; then
    exit 0
  fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "tmux-wait.sh: timed out waiting for '${pattern}' on ${target}" >&2
    exit 1
  fi
  sleep 0.5
done
