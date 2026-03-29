#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook for Agent: blocks the built-in claude-code-guide subagent
# and redirects to wiggum-util:claude-code-guide.

input=$(cat)
subagent_type=$(jq -r '.tool_input.subagent_type // empty' <<< "$input")
[ -z "$subagent_type" ] && exit 0

# Block the built-in claude-code-guide (unqualified name).
# The plugin agent wiggum-util:claude-code-guide passes through.
if [ "$subagent_type" = "claude-code-guide" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Use wiggum-util:claude-code-guide instead of the built-in claude-code-guide"}}'
  exit 0
fi

exit 0
