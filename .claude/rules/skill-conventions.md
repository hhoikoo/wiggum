---
paths:
  - "plugins/*/skills/**"
  - ".claude/skills/**"
---
# Skill Definition Conventions

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

## DCI and `allowed-tools`

DCI (Dynamic Context Injection) commands (`` !`command` `` syntax) bypass the PreToolUse hook system and are checked directly against the permission rules engine. Without an `allowed-tools` entry, DCI commands fail for users who have not manually added a matching `permissions.allow` rule. To ensure DCI works for all plugin users, every skill that uses DCI must declare `allowed-tools` in its frontmatter covering the DCI commands. The standard patterns:

```yaml
allowed-tools:
  - Bash(*/scripts/*.sh)
  - Bash(*/scripts/*.sh *)
```

The `*` prefix matches config directory paths (the shell expands it at execution time). `allowed-tools` is additive -- it auto-approves the listed tools without restricting access to unlisted tools.

## DCI in Prose

When referencing a DCI command in skill prose, always use a fenced code block. Never wrap DCI syntax in inline markdown backticks -- the backticks in `` !`command` `` conflict with markdown code span parsing and break the DCI preprocessor.

## Quality Rules

- No hallucinated tools. Every tool referenced must actually exist.
- No conflicting instructions. If two files disagree, the more specific one wins (skill > agent > rule).
- Prompts are code. Review them with the same rigor as source code.
- Every frontmatter field must be a real field supported by Claude Code. Do not invent fields.
- When unsure about Claude Code features, launch a `cc-guide` agent rather than guessing.
