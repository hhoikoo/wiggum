---
name: rebase-resolve-conflicts
description: Rebase the current branch onto its base branch and resolve merge conflicts. Use when the base branch has advanced and the current branch needs to incorporate upstream changes.
allowed-tools:
  - Bash($CLAUDE_PROJECT_DIR/.claude/scripts/*.sh)
  - Bash($CLAUDE_PROJECT_DIR/.claude/scripts/*.sh *)
  - Bash(git *)
  - "Bash(uv run pre-commit run --all-files)"
  - Read
  - Edit
---

# Rebase and Resolve Conflicts

Rebase the current branch onto its base branch, resolving any merge conflicts that arise.

## Workflow

### 1. Resolve Base Branch

```bash
.claude/scripts/resolve-base-branch.sh
```

### 2. Fetch and Check

```bash
git fetch origin <base>
```

Check if a rebase is needed:

```bash
git log HEAD..origin/<base> --oneline
```

If no commits are returned, the branch is already up to date. Report this and stop.

### 3. Rebase

```bash
git rebase origin/<base>
```

If the rebase completes without conflicts, skip to step 5.

### 4. Resolve Conflicts

For each conflict:

1. List conflicting files: `git diff --name-only --diff-filter=U`.
2. Read each conflicting file and understand both sides of the conflict.
3. Read the git log for the base branch commits that touch the conflicting files to understand the intent of upstream changes: `git log HEAD..origin/<base> -- <file>`.
4. Resolve the conflict by editing the file -- remove all conflict markers and produce the correct merged result that preserves the intent of both sides.
5. Stage the resolved file: `git add <file>`.
6. Continue the rebase: `git rebase --continue`.
7. If further conflicts arise, repeat from step 4.1.

If a conflict is ambiguous and both sides make incompatible changes to the same logic, ask the user which side to prefer before proceeding.

### 5. Verify

Run `uv run pre-commit run --all-files` to confirm the rebased code still passes.

If verification fails, diagnose and fix the issue, then amend the relevant commit:

```bash
git add <fixed-files>
git commit --amend --no-edit
```

### 6. Push

If the branch tracks a remote, force-push with lease:

```bash
git push --force-with-lease
```

If no remote tracking branch exists, skip the push and inform the user.

### 7. Report

Print a summary:

```
Rebased <branch> onto <base> (<N> commits replayed).
Conflicts resolved: <list of files, or "none">
Verification: passed
```

## Rules

- Always use `--force-with-lease`, never `--force`.
- If the rebase produces more than 5 conflicting files in a single step, pause and ask the user whether to continue or abort (`git rebase --abort`).
- Do not skip verification after rebase.
- If verification fails and the fix is non-trivial, ask the user before amending.

$ARGUMENTS
