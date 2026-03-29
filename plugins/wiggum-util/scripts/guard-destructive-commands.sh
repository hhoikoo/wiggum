#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook for Bash: blocks destructive commands that should never
# run in this project. Commands that are sometimes legitimate (rm -rf,
# git reset --hard, git branch -D, git checkout/restore .) are intentionally
# not blocked here because hooks have no user-override mechanism.

input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name // ""')

if [ "$tool" != "Bash" ]; then
  exit 0
fi

cmd=$(echo "$input" | jq -r '.tool_input.command // ""')

block() {
  local reason="$1"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}' "$reason"
  exit 0
}

# -- git push --force (but allow --force-with-lease) -----------------------
if echo "$cmd" | grep -qE 'git\s+push\s+.*--force' && \
   ! echo "$cmd" | grep -q '\-\-force-with-lease'; then
  block "Use --force-with-lease instead of --force"
fi

# -- git push to main/master -----------------------------------------------
if echo "$cmd" | grep -qE 'git\s+push' && \
   echo "$cmd" | grep -qE '(^|[[:space:]])(main|master)([[:space:]]|$)|:(\+?)(main|master)([[:space:]]|$)'; then
  block "Do not push directly to main/master"
fi

# -- git clean -f (delete untracked files) ----------------------------------
if echo "$cmd" | grep -qE 'git\s+clean\s+.*-f'; then
  block "git clean -f deletes untracked files permanently"
fi

# -- wrong package managers -------------------------------------------------
if echo "$cmd" | grep -qE '^\s*(pip|poetry|conda|npm|yarn|pnpm)\s+install'; then
  block "Use 'uv add' or 'uv pip install' instead. This is a uv-managed Python project."
fi

# -- direct pytest (use uv run instead) ------------------------------------
if echo "$cmd" | grep -qE '^\s*pytest\b'; then
  block "Use 'uv run pytest' instead of running pytest directly"
fi

exit 0
