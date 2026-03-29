#!/usr/bin/env bash
set -euo pipefail

# Clean up tmux window, git worktree, and local branch for a proposal ticket.
# Idempotent -- safe to run if any resource is already gone.
# Dependencies: tmux, git
# Usage: prd-close.sh <ticket-id> <repo-path>
# Stdout: JSON summary of what was cleaned up
# Stderr: progress diagnostics

ticket_id="${1:?Usage: prd-close.sh <ticket-id> <repo-path>}"
repo_path="${2:?Usage: prd-close.sh <ticket-id> <repo-path>}"

repo_name="$(basename "$repo_path")"
session_name="wiggum-${repo_name}"
worktree_path="${repo_path}/.wiggum/worktrees/${ticket_id}"
branch_name="doc/prd-${ticket_id}"

tmux_closed="false"
worktree_removed="false"
branch_deleted="false"

# --- Kill tmux window ---

if tmux has-session -t "$session_name" 2>/dev/null; then
  if tmux list-windows -t "$session_name" -F '#{window_name}' 2>/dev/null | grep -qx "$ticket_id"; then
    tmux kill-window -t "${session_name}:${ticket_id}"
    tmux_closed="true"
    echo "Killed tmux window ${session_name}:${ticket_id}" >&2
  else
    echo "No tmux window ${ticket_id} in session ${session_name}" >&2
  fi
else
  echo "No tmux session ${session_name}" >&2
fi

# --- Remove git worktree ---

if [ -d "$worktree_path" ]; then
  cd "$repo_path"
  git worktree remove "$worktree_path" --force
  worktree_removed="true"
  echo "Removed worktree ${worktree_path}" >&2
else
  echo "No worktree at ${worktree_path}" >&2
fi

# --- Delete local branch (only if merged) ---

cd "$repo_path"
if git show-ref --verify --quiet "refs/heads/${branch_name}"; then
  if git branch -d "$branch_name" 2>/dev/null; then
    branch_deleted="true"
    echo "Deleted branch ${branch_name}" >&2
  else
    echo "Branch ${branch_name} exists but is not fully merged -- skipping deletion" >&2
  fi
else
  echo "No local branch ${branch_name}" >&2
fi

# --- JSON summary ---

printf '{"ticket_id":"%s","tmux_closed":%s,"worktree_removed":%s,"branch_deleted":%s}\n' \
  "$ticket_id" "$tmux_closed" "$worktree_removed" "$branch_deleted"
