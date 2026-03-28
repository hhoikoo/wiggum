---
paths:
  - "plugins/*/agents/**"
  - ".claude/agents/**"
---
# Agent Definition Conventions

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

## Quality Rules

- No hallucinated tools. Every tool referenced must actually exist.
- No conflicting instructions. If two files disagree, the more specific one wins (skill > agent > rule).
- Prompts are code. Review them with the same rigor as source code.
- Every frontmatter field must be a real field supported by Claude Code. Do not invent fields.
- When unsure about Claude Code features, launch a `cc-guide` agent rather than guessing.
