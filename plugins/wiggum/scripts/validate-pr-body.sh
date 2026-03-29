#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook for Bash: validates PR body against the pull request
# template before gh pr create runs. Fetches the template from GitHub's
# default branch to always validate against the canonical version.
#
# Marker comments in the template drive validation:
#   <!-- required: Section Name -->   headings that must appear
#   <!-- required-checklist -->       checklist block whose items must appear
#   <!-- /required-checklist -->

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // ""')

if [ "$tool" != "Bash" ]; then
  exit 0
fi

cmd=$(echo "$input" | jq -r '.tool_input.command // ""')

if ! echo "$cmd" | grep -qE 'gh\s+pr\s+create'; then
  exit 0
fi

body_file=$(echo "$cmd" | grep -oE '\-\-body-file\s+[^ ]+' | awk '{print $2}')
if [ -z "$body_file" ]; then
  exit 0
fi
body_file="${body_file/#\~/$HOME}"
if [ ! -f "$body_file" ]; then
  exit 0
fi

# Fetch template from GitHub default branch (cached for 1 hour)
repo=$(cd "$CLAUDE_PROJECT_DIR" && gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null) || true
if [ -z "$repo" ]; then
  exit 0
fi
template=$(gh api --cache 1h "repos/$repo/contents/.github/PULL_REQUEST_TEMPLATE.md" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null) || true
if [ -z "$template" ]; then
  exit 0
fi

body=$(cat "$body_file")
missing=""

# Required headings: lines matching <!-- required: ... -->
while IFS= read -r marker; do
  heading=$(echo "$marker" | sed 's/.*<!-- required: //' | sed 's/ -->.*//')
  if ! echo "$body" | grep -qF "## $heading"; then
    missing="${missing}  - Missing heading: ## ${heading}\n"
  fi
done < <(echo "$template" | grep '<!-- required: .* -->')

# Required checklist: items between <!-- required-checklist --> markers
in_block=false
while IFS= read -r line; do
  if echo "$line" | grep -qF '<!-- required-checklist -->'; then
    in_block=true
    continue
  fi
  if echo "$line" | grep -qF '<!-- /required-checklist -->'; then
    in_block=false
    continue
  fi
  if $in_block && echo "$line" | grep -qE '^\* \[.\] '; then
    item_text="${line#\* \[?\] }"
    if ! echo "$body" | grep -qF "$item_text"; then
      missing="${missing}  - Missing checklist item: ${item_text}\n"
    fi
  fi
done <<< "$template"

if [ -n "$missing" ]; then
  reason="PR body does not match .github/PULL_REQUEST_TEMPLATE.md. Fix the body file and retry.\n${missing}All required headings and checklist items must be present."
  reason_escaped=$(printf '%s' "$reason" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}' "$reason_escaped"
  exit 0
fi

exit 0
