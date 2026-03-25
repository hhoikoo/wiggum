#!/usr/bin/env bash
set -euo pipefail

# PreToolUse hook for Skill: injects a system message when the agent
# auto-invokes a skill, so the user can see which skill is being used.

input=$(cat)
skill=$(echo "$input" | jq -r '.tool_input.skill // "unknown"')

printf "{\"systemMessage\": \"Auto-invoking skill \`%s\`\"}" "$skill"
