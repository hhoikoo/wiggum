#!/usr/bin/env bash
set -euo pipefail

# Resolve base branch, fetch, and start rebase. Returns conflict info if any.
# Dependencies: git, jq
# Usage: rebase-setup.sh [base-branch]
# Stdout: JSON with {needs_rebase, base_branch, conflicts: [{file, status}]}
# If no rebase needed or rebase completes cleanly, conflicts is empty.

script_dir="$(cd "$(dirname "$(realpath "${BASH_SOURCE[0]}")")" && pwd)"

if [ -n "${1:-}" ]; then
  base_branch="$1"
else
  base_branch=$("$script_dir/resolve-base-branch.sh" | jq -r '.branch // "main"' 2>/dev/null || echo "main")
fi

git fetch origin "$base_branch" >&2

behind=$(git rev-list --count "HEAD..origin/${base_branch}" 2>/dev/null || echo "0")

if [ "$behind" -eq 0 ]; then
  jq -n '{needs_rebase: false, base_branch: "'"$base_branch"'", conflicts: []}'
  exit 0
fi

# Attempt rebase -- may stop with conflicts
if git rebase "origin/${base_branch}" >&2 2>&1; then
  jq -n '{needs_rebase: false, base_branch: "'"$base_branch"'", conflicts: []}'
  exit 0
fi

# Rebase stopped with conflicts -- collect them
conflicts="[]"
while IFS= read -r line; do
  status=$(echo "$line" | cut -c1-2 | tr -d ' ')
  file=$(echo "$line" | cut -c4-)
  conflicts=$(echo "$conflicts" | jq \
    --arg file "$file" \
    --arg status "$status" \
    '. + [{file: $file, status: $status}]')
done < <(git diff --name-status --diff-filter=U)

jq -n \
  --arg base_branch "$base_branch" \
  --argjson conflicts "$conflicts" \
  '{needs_rebase: true, base_branch: $base_branch, conflicts: $conflicts}'
