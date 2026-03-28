#!/usr/bin/env bash
set -euo pipefail

# Fetch a GitHub issue body by number.
# Dependencies: gh
# Usage: fetch-issue.sh <issue-number>
# Stdout: JSON with key, summary, description, type, status fields.

issue_number="${1:?Usage: fetch-issue.sh <issue-number>}"

gh issue view "$issue_number" --json number,title,body,labels,state \
  | jq '{
    key: .number,
    summary: .title,
    description: .body,
    type: ((.labels // []) | map(.name) | map(select(startswith("type:"))) | first // "unknown"),
    status: .state
  }'
