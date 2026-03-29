#!/usr/bin/env bash
set -euo pipefail

# Push the current branch to origin, setting upstream if needed.
# Dependencies: git
# Usage: push-branch.sh
# Stdout: JSON with {branch, pushed, had_remote}

branch=$(git branch --show-current)
had_remote=false

if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  had_remote=true
  git push >&2
else
  git push -u origin HEAD >&2
fi

jq -n \
  --arg branch "$branch" \
  --argjson had_remote "$had_remote" \
  '{branch: $branch, pushed: true, had_remote: $had_remote}'
