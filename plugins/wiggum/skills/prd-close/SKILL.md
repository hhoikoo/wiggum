---
name: prd-close
description: Clean up tmux window, git worktree, and local branch after a proposal PR is merged. Run from your interactive session, not from the tmux session being closed.
argument-hint: "<ticket-id>"
---

# PRD Close

Cleans up the resources created by `/wiggum:feature-propose` after the proposal PR has been merged or abandoned. Run this from your interactive Claude Code session -- not from the tmux session being closed.

## Workflow

1. Parse `$ARGUMENTS` for the ticket ID.

2. Run the cleanup script:
   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/prd-close.sh <ticket-id> "$(git rev-parse --show-toplevel)"
   ```

3. Report the JSON output to the user, summarizing what was cleaned up:
   - tmux window killed (or already gone)
   - worktree removed (or already gone)
   - local branch deleted (or not fully merged / already gone)

## Rules

- This skill is idempotent. Safe to run multiple times -- it skips resources that are already gone.
- Do not prompt for confirmation. The user explicitly invoked this skill.
- If the script fails, report the error and stop. Do not retry.

$ARGUMENTS
