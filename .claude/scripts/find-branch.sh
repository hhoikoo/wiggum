#!/usr/bin/env bash
set -euo pipefail

# Find a remote branch by issue number.
# Searches for branches containing the issue number as a path segment.
# Returns the branch name or empty string.
# Usage: find-branch.sh <ISSUE_NUMBER>

issue_number="${1:?Usage: find-branch.sh <ISSUE_NUMBER>}"

branches=()
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  ref=$(echo "$line" | awk '{print $2}')
  branch="${ref#refs/heads/}"
  branches+=("$branch")
done < <(git ls-remote --heads origin 2>/dev/null | grep -E "/${issue_number}(/|$)" || true)

if [[ ${#branches[@]} -eq 0 ]]; then
  echo ""
  exit 0
fi

if [[ ${#branches[@]} -gt 1 ]]; then
  echo "Warning: multiple branches found for issue ${issue_number}, using first match" >&2
fi

echo "${branches[0]}"
