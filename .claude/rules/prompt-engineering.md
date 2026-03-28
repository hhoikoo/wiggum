---
paths:
  - "plugins/**/*.{md,json,sh}"
  - ".claude/**/*"
---
# Prompt Engineering Conventions

Common rules for writing and maintaining agent definitions, skill files, and hooks.

## File Types and Locations

| Type | Location |
|------|----------|
| Agent definitions | `plugins/<name>/agents/*.md` or `.claude/agents/*.md` |
| Skills | `plugins/<name>/skills/<skill>/SKILL.md` or `.claude/skills/<skill>/SKILL.md` |
| Hooks | `plugins/<name>/hooks/hooks.json` or `.claude/settings.json` |

## Quality Rules

- No hallucinated tools. Every tool referenced in an agent or skill must actually exist.
- No conflicting instructions. If two files disagree, the more specific one wins (skill > agent > rule).
- Prompts are code. Review them with the same rigor as source code: test that they produce the expected behavior, version them, diff them.
- Every frontmatter field must be a real field supported by Claude Code. Do not invent fields.
- **When unsure about Claude Code features** (supported frontmatter fields, tool names, hook events, etc.), launch a `cc-guide` agent rather than guessing or relying on training data. It carries a documentation map and searches GitHub issues for known problems. Launch multiple agents in parallel when researching different aspects.
