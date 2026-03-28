#!/usr/bin/env bash
set -euo pipefail

# Create a git worktree, launch a Claude session in a tmux window, and send an initial command.
# Dependencies: tmux, git, claude, jq
# Usage: session-launch.sh --ticket-id <ID> --repo-path <PATH> --base-branch <BRANCH> --command <CMD>
# Stdout: tmux target (session:window)

script_dir="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
tmux_send="${script_dir}/tmux-send.sh"
tmux_wait="${script_dir}/tmux-wait.sh"

ticket_id=""
repo_path=""
base_branch="main"
launch_command=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ticket-id)
      ticket_id="${2:?--ticket-id requires a value}"
      shift 2
      ;;
    --repo-path)
      repo_path="${2:?--repo-path requires a value}"
      shift 2
      ;;
    --base-branch)
      base_branch="${2:?--base-branch requires a value}"
      shift 2
      ;;
    --command)
      launch_command="${2:?--command requires a value}"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$ticket_id" ] || [ -z "$repo_path" ]; then
  echo "session-launch.sh: --ticket-id and --repo-path are required" >&2
  exit 1
fi

repo_name="$(basename "$repo_path")"
session_name="wiggum-${repo_name}"
worktree_path="${repo_path}/.wiggum/worktrees/${ticket_id}"
branch_name="doc/prd-${ticket_id}"

# --- Worktree creation ---

if [ -d "$worktree_path" ]; then
  echo "Worktree already exists at ${worktree_path}" >&2
else
  mkdir -p "$(dirname "$worktree_path")"
  cd "$repo_path"
  git fetch origin "$base_branch"

  if git show-ref --verify --quiet "refs/heads/${branch_name}"; then
    git worktree add "$worktree_path" "$branch_name"
  else
    git worktree add -b "$branch_name" "$worktree_path" "origin/${base_branch}"
  fi

  # Symlink settings.local.json so the worktree inherits permissions
  source_settings="${repo_path}/.claude/settings.local.json"
  target_settings="${worktree_path}/.claude/settings.local.json"
  if [ -f "$source_settings" ] && [ ! -e "$target_settings" ]; then
    mkdir -p "${worktree_path}/.claude"
    ln -s "$source_settings" "$target_settings"
    echo "Symlinked .claude/settings.local.json" >&2
  fi

  # Pre-accept the Claude Code trust dialog for the worktree path
  tmp_file="/tmp/wiggum-trust-$(uuidgen).json"
  jq --arg p "$worktree_path" \
    '.projects[$p] = {"hasTrustDialogAccepted": true, "hasCompletedProjectOnboarding": true, "allowedTools": [], "projectOnboardingSeenCount": 1}' \
    ~/.claude.json > "$tmp_file" && cp "$tmp_file" ~/.claude.json && rm "$tmp_file"
  echo "Trust accepted for worktree: ${worktree_path}" >&2
fi

# --- tmux session/window creation ---

if ! tmux has-session -t "$session_name" 2>/dev/null; then
  tmux new-session -d -s "$session_name" -n "$ticket_id" -c "$worktree_path"
else
  if tmux list-windows -t "$session_name" -F '#{window_name}' 2>/dev/null | grep -qx "$ticket_id"; then
    echo "Window ${session_name}:${ticket_id} already exists, skipping launch" >&2
    echo "${session_name}:${ticket_id}"
    exit 0
  fi
  tmux new-window -t "$session_name" -n "$ticket_id" -c "$worktree_path"
fi

target="${session_name}:${ticket_id}"

# --- Claude launch ---

"$tmux_send" "$target" "claude --dangerously-skip-permissions"

# Wait for the Claude process to appear
deadline=$(( $(date +%s) + 30 ))
while true; do
  if pgrep -x claude >/dev/null 2>&1; then break; fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "session-launch.sh: timed out waiting for claude process" >&2
    exit 1
  fi
  sleep 0.5
done

# Wait for Claude TUI prompt
sleep 5
"$tmux_wait" "$target" "❯" 30

# --- Send initial command ---

if [ -n "$launch_command" ]; then
  tmux send-keys -l -t "$target" "$launch_command"
  sleep 1
  tmux send-keys -t "$target" Enter
fi

echo "$target"
