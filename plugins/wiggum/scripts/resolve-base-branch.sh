#!/usr/bin/env bash
set -euo pipefail

# Resolve the base branch for the current working directory.
# Checks: upstream tracking branch -> main
# Usage: resolve-base-branch.sh
# Output: prints the resolved base branch name to stdout

current_branch=$(git branch --show-current)

# 1. Fall back to upstream tracking branch
upstream=$(git rev-parse --abbrev-ref '@{u}' 2>/dev/null | sed 's|^origin/||') || upstream=""
if [[ -n "$upstream" && "$upstream" != "$current_branch" ]]; then
  echo "$upstream"
  exit 0
fi

# 2. Default to main
echo "main"
