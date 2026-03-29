#!/usr/bin/env bash
set -euo pipefail

# Fetch all CI checks for the current branch's PR, filter to failing ones, and fetch log excerpts.
# Dependencies: gh, jq
# Usage: fetch-failing-checks.sh [pr-number]
# Stdout: JSON array of {name, status, conclusion, log_url, log_excerpt}

pr_number="${1:-}"

if [ -z "$pr_number" ]; then
  pr_number=$(gh pr view --json number --jq '.number' 2>/dev/null || true)
  if [ -z "$pr_number" ]; then
    echo "No PR found for current branch" >&2
    exit 1
  fi
fi

checks_json=$(gh pr checks "$pr_number" --json name,state,conclusion,detailsUrl 2>/dev/null || echo "[]")

failing=$(echo "$checks_json" | jq '[.[] | select(.conclusion == "FAILURE" or .conclusion == "failure" or .state == "FAILURE")]')
count=$(echo "$failing" | jq 'length')

if [ "$count" -eq 0 ]; then
  echo "[]"
  exit 0
fi

result="[]"
for i in $(seq 0 $((count - 1))); do
  name=$(echo "$failing" | jq -r ".[$i].name")
  conclusion=$(echo "$failing" | jq -r ".[$i].conclusion")
  details_url=$(echo "$failing" | jq -r ".[$i].detailsUrl")

  log_excerpt=""
  if [ "$details_url" != "null" ] && [ -n "$details_url" ]; then
    run_id=$(echo "$details_url" | grep -oE '[0-9]+' | tail -1)
    if [ -n "$run_id" ]; then
      log_excerpt=$(gh run view "$run_id" --log-failed 2>/dev/null | tail -50 || true)
    fi
  fi

  result=$(echo "$result" | jq \
    --arg name "$name" \
    --arg conclusion "$conclusion" \
    --arg details_url "$details_url" \
    --arg log_excerpt "$log_excerpt" \
    '. + [{name: $name, conclusion: $conclusion, log_url: $details_url, log_excerpt: $log_excerpt}]')
done

echo "$result"
