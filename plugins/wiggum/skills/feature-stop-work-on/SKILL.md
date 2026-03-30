---
name: feature-stop-work-on
description: Stop implementation work on a feature. Creates or updates a PR, removes the worktree, kills the tmux window, and prunes git references.
argument-hint: "[ticket-number]"
---

# Feature Stop Work On

Gracefully stops implementation work on a feature by creating/updating a PR, tearing down the worktree, and cleaning up the tmux session.

## Phase 1: Resolve Ticket

Determine the implementation ticket number from one of these sources (in priority order):

1. `$ARGUMENTS` -- the user passed a ticket number explicitly.
2. Current worktree path -- if working inside `.wiggum/worktrees/<ticket>/`, extract `<ticket>` from the path.
3. Current branch name -- extract the ticket ID from the branch (e.g., `feat/<ticket>/slug`).

If none of these resolve a ticket number, stop with an error: "Could not determine ticket number. Pass it explicitly: /wiggum:feature-stop-work-on <ticket-number>"

## Phase 2: Derive Naming

Compute these values for later steps:

- **repo-path**: `git rev-parse --show-toplevel` (resolve from the main repo, not a worktree)
- **repo-name**: `basename "$(git remote get-url origin)" .git`
- **worktree-path**: `<repo-path>/.wiggum/worktrees/<ticket>`
- **branch-name**: read from the worktree's HEAD if the worktree exists, otherwise from the current branch

To find the tmux session and window:

- **feature-slug**: extract from branch-name (the part after `feat/<ticket>/`)
- **session-name**: `wiggum-<repo-name>-<feature-slug>`
- **window-name**: `<ticket>`

## Phase 3: Check Working Tree

If the worktree directory exists, check for uncommitted changes:

```bash
git -C <worktree-path> status --porcelain
```

If there are uncommitted changes, refuse with a warning:

```
Uncommitted changes in worktree:
<list of files from git status>

Commit or stash changes before stopping work.
```

Exit with code 1. Do not proceed.

If the worktree does not exist, skip this check (it was already cleaned up).

## Phase 4: Push and Create PR

If the worktree exists and has commits ahead of origin, push and create a PR:

1. Change to the worktree directory.
2. Delegate to `/wiggum:create-pr --no-review` to push the branch and create or update the PR.

If the worktree does not exist, check whether the branch exists on the remote:

```bash
git ls-remote --exit-code --heads origin <branch-name>
```

If it does, check out the branch locally (if not already checked out) and delegate to `/wiggum:create-pr --no-review`.

If neither the worktree nor the remote branch exist, skip PR creation.

## Phase 5: Remove Worktree

If the worktree directory exists, remove it:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/worktree-remove.sh \
  --worktree-path <worktree-path> \
  --repo-path <repo-path>
```

This is idempotent -- it succeeds if the worktree is already removed.

## Phase 6: Kill tmux Window

Clean up the tmux window and session:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/tmux-kill-window.sh \
  --session <session-name> \
  --window <window-name>
```

This is idempotent -- it succeeds if the window or session does not exist.

## Phase 7: Report

Print a summary:

```
Implementation work stopped for #<ticket>

Cleanup:
  PR:        <PR URL> (or "skipped -- no commits to push")
  Worktree:  removed (or "already removed")
  tmux:      window killed (or "already removed")
  Branch:    <branch-name> (remote only, local worktree removed)
```

## Rules

- Always delegate PR creation to `/wiggum:create-pr`. Never create PRs directly.
- Never remove a worktree with uncommitted changes. Always refuse and let the user decide.
- All cleanup steps (worktree removal, tmux kill) are idempotent. Running this skill twice produces the same result.
- If the worktree does not exist, skip directly to the steps that still apply (tmux cleanup, reporting).

$ARGUMENTS
