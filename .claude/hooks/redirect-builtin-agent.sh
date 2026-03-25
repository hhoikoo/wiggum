#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook for Agent: blocks the built-in claude-code-guide subagent
# and redirects to the project-local cc-guide agent.

input=$(cat)
subagent_type=$(jq -r '.tool_input.subagent_type // empty' <<< "$input")
[ -z "$subagent_type" ] && exit 0

# Block the built-in claude-code-guide (unqualified name).
# The project agent cc-guide passes through.
if [ "$subagent_type" = "claude-code-guide" ]; then
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Use cc-guide instead of the built-in claude-code-guide"}}'
  exit 0
fi

exit 0
