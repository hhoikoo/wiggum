#!/usr/bin/env bash
set -euo pipefail

# Ensure a PR body references an issue. Appends "resolves #<id>" if not already present.
# Usage: pr-link-issue.sh <pr-number> <ticket-id>

pr_number="${1:?Usage: pr-link-issue.sh <pr-number> <ticket-id>}"
ticket_id="${2:?Usage: pr-link-issue.sh <pr-number> <ticket-id>}"

body=$(gh pr view "$pr_number" --json body -q .body)
if echo "$body" | grep -qF "#${ticket_id}"; then
  exit 0
fi

tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
printf '%s\n\nresolves #%s\n' "$body" "$ticket_id" > "$tmp"
gh pr edit "$pr_number" --body-file "$tmp"
