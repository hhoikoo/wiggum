#!/usr/bin/env bash
set -euo pipefail

# Resolve base branch, fetch origin, check for upstream changes, and merge if needed.
# Dependencies: git, jq
# Usage: setup-branch.sh [base-branch]
# Stdout: JSON with {base_branch, current_branch, upstream_commits, merged, stashed}

script_dir="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"
base_branch=$("$script_dir/resolve-base-branch.sh" | jq -r '.branch // "main"' 2>/dev/null || echo "main")

current_branch=$(git branch --show-current)
upstream_commits=0
merged=false
stashed=false

git fetch origin "$base_branch" >&2

upstream_commits=$(git rev-list --count "HEAD..origin/${base_branch}" 2>/dev/null || echo "0")

if [ "$upstream_commits" -gt 0 ] && [ "$current_branch" = "$base_branch" ]; then
  if [ -n "$(git status --porcelain)" ]; then
    git stash >&2
    stashed=true
  fi
  git merge --ff-only "origin/${base_branch}" >&2
  merged=true
  if [ "$stashed" = true ]; then
    git stash pop >&2
  fi
fi

jq -n \
  --arg base_branch "$base_branch" \
  --arg current_branch "$current_branch" \
  --argjson upstream_commits "$upstream_commits" \
  --argjson merged "$merged" \
  --argjson stashed "$stashed" \
  '{base_branch: $base_branch, current_branch: $current_branch, upstream_commits: $upstream_commits, merged: $merged, stashed: $stashed}'
