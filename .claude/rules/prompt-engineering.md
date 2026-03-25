---
paths:
  - "plugins/**/*.md"
  - "plugins/**/*.json"
  - ".claude/**/*.md"
  - ".claude/**/*.json"
---
# Prompt Engineering Conventions

Rules for writing and maintaining agent definitions, skill files, and hooks in plugins.

## File Types and Locations

| Type | Location |
|------|----------|
| Agent definitions | `plugins/<name>/agents/*.md` |
| Skills | `plugins/<name>/skills/<skill>/SKILL.md` |
| Hooks | `plugins/<name>/hooks/hooks.json` |

## Agent Definition Format

Agent files use YAML frontmatter followed by markdown instructions. Supported frontmatter fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Lowercase letters, numbers, hyphens. Unique identifier. |
| `description` | Yes | When Claude should delegate to this agent. |
| `model` | No | `sonnet`, `opus`, `haiku`, or `inherit` (default). |
| `tools` | No | List of tool names the agent can use. Inherits all if omitted. |
| `disallowedTools` | No | Tools to deny, removed from inherited set. |
| `maxTurns` | No | Maximum agentic turns before stopping. |
| `skills` | No | Skill names to preload into context. |
| `hooks` | No | Hook configuration scoped to this agent. |

## Skill Definition Format

Skill files live at `<dir>/SKILL.md` with YAML frontmatter. Supported frontmatter fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Lowercase letters, numbers, hyphens. Defaults to directory name. |
| `description` | Recommended | What the skill does and when to use it. |
| `argument-hint` | No | Hint shown during autocomplete (e.g., `[ticket-id]`). |
| `disable-model-invocation` | No | Prevent Claude from auto-loading. Default: `false`. |
| `user-invocable` | No | Show in `/` menu. Default: `true`. |
| `compatibility` | No | Version or compatibility metadata. |
| `license` | No | License identifier. |
| `metadata` | No | Arbitrary key-value metadata. |

String substitutions: `$ARGUMENTS` (all args), `$ARGUMENTS[N]` or `$N` (specific arg by index).

### DCI and `allowed-tools`

DCI (Dynamic Context Injection) commands (`` !`command` `` syntax) bypass the PreToolUse hook system and are checked directly against the permission rules engine. Without an `allowed-tools` entry, DCI commands fail for users who have not manually added a matching `permissions.allow` rule. To ensure DCI works for all plugin users, every skill that uses DCI must declare `allowed-tools` in its frontmatter covering the DCI commands. Use `$AUTOCODE_CONFIG_DIR` (no braces) in DCI commands -- Claude Code's permission system rejects `${}` parameter substitution. The standard patterns:

```yaml
allowed-tools:
  - Bash(*/scripts/*.sh)
  - Bash(*/scripts/*.sh *)
```

The `*` prefix matches `$AUTOCODE_CONFIG_DIR` (the shell expands it at execution time). The first pattern matches no-argument calls; the second matches calls with arguments. `allowed-tools` is additive -- it auto-approves the listed tools without restricting access to unlisted tools.

### DCI in prose

When referencing a DCI command in skill prose, always use a fenced code block. Never wrap DCI syntax in inline markdown backticks -- the backticks in `` !`command` `` conflict with markdown code span parsing and break the DCI preprocessor.

# Wrong -- backticks collide, DCI breaks:
run `!`$AUTOCODE_CONFIG_DIR/scripts/resolve.sh plugin script.sh`` with args

# Right -- fenced code block:
run check-unresponded-pr.sh:
   ```bash
   !`$AUTOCODE_CONFIG_DIR/scripts/resolve.sh plugin script.sh` <args>
   ```

## Hook Conventions

Hooks are configured in plugin `hooks.json` files or `.claude/settings.json`.

### Event types

`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostToolUseFailure`, `Notification`, `SubagentStart`, `SubagentStop`, `Stop`, `TeammateIdle`, `TaskCompleted`, `PreCompact`, `SessionEnd`.

### Handler types

- `command` -- shell command. Receives JSON on stdin, outputs JSON on stdout. Exit code controls behavior.
- `prompt` -- sends the prompt and hook input to a model (Haiku by default). The model returns `{"ok": true/false, "reason": "..."}` to allow or block the action. Use `model` field to override.
- `agent` -- spawns a subagent with tool access (up to 50 turns, 60s default timeout). Returns `{"ok": true/false, "reason": "..."}` like `prompt` hooks, but can read files, run commands, etc.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success. Parse stdout for JSON output. |
| 2 | Blocking error. Stderr fed to Claude as error context. |
| Other | Non-blocking error. Stderr shown in verbose mode. |

### JSON output fields (stdout, exit 0)

Universal fields (all events): `continue` (bool), `stopReason` (string), `suppressOutput` (bool), `systemMessage` (string).

Event-specific fields:
- `decision` ("block") + `reason` -- used by `UserPromptSubmit`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStop`.
- `hookSpecificOutput.permissionDecision` ("allow"/"deny"/"ask") + `hookSpecificOutput.permissionDecisionReason` -- used by `PreToolUse`.
- `hookSpecificOutput.decision.behavior` ("allow"/"deny") -- used by `PermissionRequest`.

### Environment variables

- `$CLAUDE_PROJECT_DIR` -- project root. Available to all command hooks.
- `$CLAUDE_ENV_FILE` -- file path for persisting env vars via `export` statements. SessionStart hooks only.
- `$CLAUDE_PLUGIN_ROOT` -- plugin root directory. Plugin-provided hooks only.

## Quality Rules

- No hallucinated tools. Every tool referenced in an agent or skill must actually exist.
- No conflicting instructions. If two files disagree, the more specific one wins (skill > agent > rule).
- Prompts are code. Review them with the same rigor as source code: test that they produce the expected behavior, version them, diff them.
- Every frontmatter field must be a real field supported by Claude Code. Do not invent fields.
- **When unsure about Claude Code features** (supported frontmatter fields, tool names, hook events, etc.), launch a `claude-code-guide` agent via Task tool (`subagent_type: "autocode-core:claude-code-guide"`) rather than guessing or relying on training data. It carries a documentation map and searches GitHub issues for known problems. Launch multiple agents in parallel when researching different aspects.
