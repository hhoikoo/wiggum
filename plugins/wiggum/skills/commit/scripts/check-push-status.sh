#!/usr/bin/env bash
set -euo pipefail

# Check if the current branch is ahead of its remote tracking branch and push if so.
# Dependencies: git
# Usage: check-push-status.sh
# Stdout: JSON with {has_remote, ahead, pushed, branch}

branch=$(git branch --show-current)
has_remote=false
ahead=0
pushed=false

if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  has_remote=true
  ahead=$(git rev-list --count '@{u}..HEAD')
  if [ "$ahead" -gt 0 ]; then
    git push >&2
    pushed=true
  fi
fi

jq -n \
  --arg branch "$branch" \
  --argjson has_remote "$has_remote" \
  --argjson ahead "$ahead" \
  --argjson pushed "$pushed" \
  '{branch: $branch, has_remote: $has_remote, ahead: $ahead, pushed: $pushed}'
