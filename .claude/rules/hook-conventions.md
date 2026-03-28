---
paths:
  - "plugins/*/hooks/**"
  - ".claude/hooks/**"
  - ".claude/settings.json"
  - ".claude/settings.local.json"
---
# Hook Conventions

Hooks are configured in plugin `hooks.json` files or `.claude/settings.json`.

## Event Types

`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `TeammateIdle`, `TaskCompleted`, `PreCompact`, `SessionEnd`.

## Handler Types

- `command` -- shell command. Receives JSON on stdin, outputs JSON on stdout. Exit code controls behavior.
- `prompt` -- sends the prompt and hook input to a model (Haiku by default). The model returns `{"ok": true/false, "reason": "..."}` to allow or block the action. Use `model` field to override.
- `agent` -- spawns a subagent with tool access (up to 50 turns, 60s default timeout). Returns `{"ok": true/false, "reason": "..."}` like `prompt` hooks, but can read files, run commands, etc.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success. Parse stdout for JSON output. |
| 2 | Blocking error. Stderr fed to Claude as error context. |
| Other | Non-blocking error. Stderr shown in verbose mode. |

## JSON Output Fields (stdout, exit 0)

Universal fields (all events): `continue` (bool), `stopReason` (string), `suppressOutput` (bool), `systemMessage` (string).

Event-specific fields:
- `decision` ("block") + `reason` -- used by `UserPromptSubmit`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStop`.
- `hookSpecificOutput.permissionDecision` ("allow"/"deny"/"ask") + `hookSpecificOutput.permissionDecisionReason` -- used by `PreToolUse`.
- `hookSpecificOutput.decision.behavior` ("allow"/"deny") -- used by `PermissionRequest`.

## Environment Variables

- `$CLAUDE_PROJECT_DIR` -- project root. Available to all command hooks.
- `$CLAUDE_ENV_FILE` -- file path for persisting env vars via `export` statements. SessionStart hooks only.
- `$CLAUDE_PLUGIN_ROOT` -- plugin root directory. Plugin-provided hooks only.
