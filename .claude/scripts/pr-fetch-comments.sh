#!/usr/bin/env bash
set -euo pipefail

# Fetch review comments for a PR.
# Usage: pr-fetch-comments.sh <pr-number>
# Output: JSON array of {id, node_id, path, line, body, user, created_at, in_reply_to_id}

pr_number="${1:?Usage: pr-fetch-comments.sh <pr-number>}"
repo=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')

gh api "repos/${repo}/pulls/${pr_number}/comments" --paginate | \
  jq -sc '(add // []) | [.[] | {id, node_id, path, line, body, user: .user.login, created_at, in_reply_to_id}]'
