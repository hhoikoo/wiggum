# Research: Plugin, Skills, and Agents Structure

## Question

How are wiggum plugins, skills, and agents structured? What conventions do they follow?

## Findings

### Two-Plugin Architecture

- `wiggum` (core Ralph Loop PRD engine) at `./plugins/wiggum`
- `wiggum-util` (convenience utilities) at `./plugins/wiggum-util`
- Dependency rule: wiggum-util may reference wiggum, never the reverse
- Marketplace manifest: `.claude-plugin/marketplace.json`

### Skill Directory Layout

```
plugins/wiggum/skills/<name>/
  SKILL.md              # canonical definition with YAML frontmatter
  scripts/
    shared-script.sh -> ../../../scripts/shared-script.sh  (symlink)
    skill-specific.sh                                       (local)
```

- Shared scripts in `plugins/wiggum/scripts/`, symlinked per-skill
- Scripts referenced via `${CLAUDE_SKILL_DIR}/scripts/<name>.sh`
- `${CLAUDE_PLUGIN_ROOT}` banned due to bugs (anthropics/claude-code#9354, #38699, #39328)

### Skill Inventory (wiggum plugin)

| Skill | Role |
|-------|------|
| `propose-feature` | Interactive: gathers idea, creates ticket, spawns background PRD session |
| `create-feature-prd` | Autonomous orchestrator: parallel research, draft PRD, refinement, PR |
| `review-feature-prd` | Handles review comments on PRD PR |
| `commit` | Conventional commit with pre-commit hook handling |
| `create-branch` | Branch creation in ticket or description mode |
| `create-issue` | GitHub issue creation |
| `create-pr` | PR creation with body validation |

### Agent Definitions

| Agent | Model | Tools | Role |
|-------|-------|-------|------|
| `prd-writer` | inherit | Read, Write, Glob, Grep | Synthesizes research into PRD |
| `codebase-researcher` | sonnet | Glob, Grep, Read | Read-only codebase exploration |
| `cross-project-researcher` | sonnet | Bash, Glob, Grep, Read, WebSearch, WebFetch | Cross-project pattern research |
| `web-researcher` | sonnet | WebSearch, WebFetch | Online topic research |

### Orchestrator Pattern

- Heavy-lifting skills never load full file content into main context
- All reads/writes of heavy content delegated to subagents
- Research subagents launched in single message for parallelism
- Each subagent gets focused, self-contained task -- no conversation history

### Hooks

- `PreToolUse` hook on `Bash` validates PR body against `.github/PULL_REQUEST_TEMPLATE.md`
- Uses `${CLAUDE_PLUGIN_ROOT}` (only supported variable for hooks)

## Gaps

- `review-feature-prd` references scripts that may live in `wiggum-util` (potential dependency violation)
- No skill uses the `skills:` frontmatter field documented in agent conventions
