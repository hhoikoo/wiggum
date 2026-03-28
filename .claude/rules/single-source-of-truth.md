---
paths:
  - ".github/**"
  - ".claude/**"
  - "plugins/**"
  - "*.md"
  - "*.yml"
  - "*.yaml"
  - "*.json"
  - "*.toml"
---
# Single Source of Truth

Applies to configuration, templates, structural definitions, and other non-code artifacts. Do not duplicate definitions across files. When a canonical source exists, reference it at runtime -- do not create parallel files that restate the same structure.

This rule does NOT apply to source code. Code duplication is a judgment call governed by existing code conventions (prefer simple repetition over premature abstraction).

## Canonical Sources

| What | Canonical Location | Consumers |
|------|-------------------|-----------
| Issue tracking | GitHub Issues (canonical source for issue details, acceptance criteria, and status) | Skills/agents reference GitHub issues for requirements |
| Issue templates | `.github/ISSUE_TEMPLATE/` | Skills that create issues use the label conventions defined here |
| PR structure | `.github/PULL_REQUEST_TEMPLATE.md` | Skills/agents that create PRs read this file to derive sections |
| Issue types | `.autocode/providers/issue-tracker/issue-types.yml` | Label-to-commit-type mappings |
| Labels | GitHub (managed via `gh label` CLI) | Skills reference label names but do not define or catalog them |
| Skill definitions | `plugins/*/skills/<name>/SKILL.md` | Agents delegate to skills, not inline their logic |
| Agent definitions | `plugins/*/agents/*.md` | Skills delegate to agents, not inline their logic |
| Conventions | `.autocode/conventions/*.md` | Skills and agents read conventions at runtime |

## Anti-Patterns

- Creating markdown body templates that mirror GitHub issue template sections.
- Hardcoding section lists in a skill when a template already defines them.
- Maintaining a label list in a config file when GitHub is the source.
- Copying a skill's workflow into an agent instead of invoking the skill.

Two files that must stay in sync will eventually diverge.
