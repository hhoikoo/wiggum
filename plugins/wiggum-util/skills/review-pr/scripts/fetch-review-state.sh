#!/usr/bin/env bash
set -euo pipefail

# Fetch review comments and unresolved threads for a PR in a single call.
# Dependencies: gh, jq
# Usage: fetch-review-state.sh [pr-number]
# Stdout: JSON with {pr_number, comments: [...], unresolved_threads: [...]}

script_dir="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"

pr_number="${1:-}"

if [ -z "$pr_number" ]; then
  pr_number=$(gh pr view --json number --jq '.number' 2>/dev/null || true)
  if [ -z "$pr_number" ]; then
    echo "No PR found for current branch" >&2
    exit 1
  fi
fi

comments=$("$script_dir/pr-fetch-comments.sh" "$pr_number")
threads=$("$script_dir/pr-fetch-threads.sh" "$pr_number")

jq -n \
  --arg pr_number "$pr_number" \
  --argjson comments "$comments" \
  --argjson threads "$threads" \
  '{pr_number: ($pr_number | tonumber), comments: $comments, unresolved_threads: $threads}'
