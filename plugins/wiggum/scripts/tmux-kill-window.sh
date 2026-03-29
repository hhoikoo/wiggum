#!/usr/bin/env bash
set -euo pipefail

# Kill a tmux window by name, cleaning up the session if no windows remain.
# Dependencies: tmux
# Usage: tmux-kill-window.sh --session <NAME> --window <NAME>
# Exit codes: 0 = success (or already removed), 1 = bad input, 2 = unexpected failure

session=""
window=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session)
      session="${2:?--session requires a value}"
      shift 2
      ;;
    --window)
      window="${2:?--window requires a value}"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$session" ] || [ -z "$window" ]; then
  echo "tmux-kill-window.sh: --session and --window are required" >&2
  exit 1
fi

# Session does not exist -- nothing to do
if ! tmux has-session -t "$session" 2>/dev/null; then
  echo "Session does not exist: ${session}" >&2
  exit 0
fi

target="${session}:${window}"

# Window does not exist -- nothing to do
if ! tmux list-windows -t "$session" -F '#{window_name}' 2>/dev/null | grep -qx "$window"; then
  echo "Window does not exist: ${target}" >&2
  exit 0
fi

# Count windows before killing
window_count="$(tmux list-windows -t "$session" 2>/dev/null | wc -l | tr -d ' ')"

if [ "$window_count" -le 1 ]; then
  # Last window -- kill the entire session
  echo "Killing session ${session} (last window)" >&2
  tmux kill-session -t "$session" 2>&1 >&2
else
  echo "Killing window ${target}" >&2
  tmux kill-window -t "$target" 2>&1 >&2
fi
