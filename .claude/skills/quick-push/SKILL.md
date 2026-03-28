---
name: quick-push
description: Ship manual changes without implementation logic. Creates a branch, commits, pushes, and opens a PR for changes already made in the current session. Use when the work is done and just needs to be shipped.
argument-hint: "type: description"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Skill
  - AskUserQuestion
  - Bash(git *)
  - Bash($CLAUDE_PROJECT_DIR/.claude/scripts/*.sh)
  - Bash($CLAUDE_PROJECT_DIR/.claude/scripts/*.sh *)
  - Bash(gh *)
  - "Bash(uv run pre-commit run --all-files)"
---

# Quick Push

Ship manual changes without implementation logic. Creates a branch, commits, pushes, and opens a PR for changes already made or described in the current session. Skips issue creation, planning, TDD, and review.

## Usage

`$ARGUMENTS` contains a type-prefixed description (e.g., `chore: update skill rules`, `fix: correct branch naming`). If omitted, ask the user what to ship.

## Pipeline

### 1. Create Branch

Invoke the `/create-branch` skill with `$ARGUMENTS` (description mode). This creates and checks out a branch named `<type>/<short-name>`.

If changes are already in the working tree (unstaged or staged), create the branch first -- git carries uncommitted changes to the new branch automatically.

### 2. Make Changes

- If the user has already made the changes (working tree is dirty), skip to step 3.
- If the user described what to change, make the changes directly. No planning agent, no TDD -- just edit the files.
- Keep changes minimal and focused.

### 3. Verify

Run `uv run pre-commit run --all-files` (format + lint + test). If it fails, fix iteratively until it passes. Do not proceed until green.

### 4. Commit

Invoke the `/wiggum:commit` skill. One logical commit covering all changes.

### 5. Create PR

Invoke the `/wiggum:create-pr` skill with `--no-review`. This pushes the branch and opens a PR without requesting reviews.

### 6. Report

Print a summary:
- PR URL
- Files changed
- Branch name

**Stop here.** Wait for the user to signal before handling reviews.

### 7. Handle post-PR events (on any user message)

When the user sends any message (e.g., "check"), evaluate the PR state:

1. Check CI status via `/fix-pr-ci` skill's step 1 (list checks). If any check is failing, invoke `/fix-pr-ci`.
2. Check for unresolved review comments. If review feedback exists, invoke `/review-pr`.
3. Check for merge conflicts. If the PR is not mergeable (base branch advanced), rebase onto the base branch, resolve conflicts, and force-push with `--force-with-lease`.
4. If CI is green, no pending reviews, and no conflicts, report the current status and wait.

## Rules

- Work autonomously. Only ask the user if the scope is ambiguous.
- Each phase delegates to the appropriate skill. Never inline work that a skill handles.
- `uv run pre-commit run --all-files` must pass before committing.
- No AI attribution anywhere -- commits, PR title, PR body.
- This skill is for small changes only. If the scope grows beyond a few files or requires design discussion, suggest creating a ticket and using a dedicated planning workflow instead.

$ARGUMENTS
