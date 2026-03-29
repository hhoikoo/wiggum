---
paths:
  - "plugins/wiggum/**"
---
# Plugin Dependency Rule

The dependency direction between wiggum plugins is one-way:

- `wiggum-util` CAN depend on skills and agents in `wiggum`
- `wiggum` CANNOT depend on skills and agents in `wiggum-util`

The `wiggum` plugin is the core Ralph Loop engine. It must remain self-contained and portable -- installable in any project without requiring `wiggum-util`. The `wiggum-util` plugin provides convenience utilities (quick-push, CI fixes, PR review, rebase) that build on top of core skills.

When adding new skills or agents to `plugins/wiggum/`, verify they do not reference any `/wiggum-util:*` skill or `wiggum-util:*` agent.
