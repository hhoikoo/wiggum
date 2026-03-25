#!/usr/bin/env bash
set -euo pipefail

# Desktop notification relay for Claude Code Notification hook events.
# Dependencies: terminal-notifier, jq (required); git, tmux (optional, for enhanced titles)
# Usage: Invoked by the Notification hook or PreToolUse hook with JSON on stdin.

if [ -n "${CLAUDE_SUPPRESS_NOTIFICATION:-}" ]; then
  exit 0
fi

if ! command -v terminal-notifier &>/dev/null; then
  exit 0
fi

input=$(cat) || exit 0
message=$(jq -r '.message // "Claude Code needs attention"' <<< "$input" 2>/dev/null) || message="Claude Code needs attention"
notification_type=$(jq -r '.notification_type // "unknown"' <<< "$input" 2>/dev/null) || notification_type="unknown"

# Build title from tmux context (session:window) or git repo+branch.
title="Claude Code"
if [ -n "${TMUX:-}" ]; then
  tmux_session=$(tmux display-message -t "$TMUX_PANE" -p '#S' 2>/dev/null) || true
  tmux_window=$(tmux display-message -t "$TMUX_PANE" -p '#W' 2>/dev/null) || true
  if [ -n "${tmux_session:-}" ] && [ -n "${tmux_window:-}" ]; then
    title="${tmux_session}:#${tmux_window}"
  fi
else
  repo=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null) || true
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || true
  if [ -n "${repo:-}" ] && [ -n "${branch:-}" ]; then
    title="${repo}:${branch}"
  fi
fi

terminal-notifier \
  -title "$title" \
  -message "$message" \
  -group "claude-${notification_type}-${title}" \
  >/dev/null 2>&1 || true
