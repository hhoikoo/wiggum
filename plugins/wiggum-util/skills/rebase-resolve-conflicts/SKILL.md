---
name: rebase-resolve-conflicts
description: Rebase the current branch onto its base branch and resolve merge conflicts. Use when the base branch has advanced and the current branch needs to incorporate upstream changes.
allowed-tools:
  - Bash(bash *)
  - Bash(git *)
  - "Bash(uv run pre-commit run --all-files)"
  - Read
  - Edit
---

# Rebase and Resolve Conflicts

Rebase the current branch onto its base branch, resolving any merge conflicts that arise.

## Workflow

### 1. Setup

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/rebase-setup.sh
```

Parse the JSON output:
- `needs_rebase: false` -- branch is up to date or rebase completed cleanly. Report and stop.
- `needs_rebase: true` -- rebase stopped with conflicts. `conflicts` contains `[{file, status}]`.

If there are more than 5 conflicting files, ask the user whether to continue or abort (`git rebase --abort`).

### 2. Resolve Conflicts

Loop over each conflicting file:

2a. Read the conflicting file to see the conflict markers.

2b. Read the git log for the base branch commits that touch this file to understand the intent of upstream changes:
```bash
git log REBASE_HEAD..HEAD -- <file>
```

2c. Resolve the conflict by editing the file -- remove all conflict markers and produce the correct merged result that preserves the intent of both sides.

2d. Stage the resolved file:
```bash
git add <file>
```

If a conflict is ambiguous and both sides make incompatible changes to the same logic, ask the user which side to prefer.

### 3. Continue Rebase

After all conflicts in this step are resolved:

```bash
git rebase --continue
```

If new conflicts arise (the rebase has multiple commits to replay), go back to step 2 with the new conflict list. Detect conflicts from the `git rebase --continue` exit code and `git diff --name-only --diff-filter=U`.

### 4. Verify

Run `uv run pre-commit run --all-files` to confirm the rebased code still passes.

If verification fails, diagnose and fix the issue, then amend the relevant commit:

```bash
git add <fixed-files>
git commit --amend --no-edit
```

### 5. Push

If the branch tracks a remote, force-push with lease:

```bash
git push --force-with-lease
```

If no remote tracking branch exists, skip the push and inform the user.

### 6. Report

```
Rebased <branch> onto <base> (<N> commits replayed).
Conflicts resolved: <list of files, or "none">
Verification: passed
```

## Rules

- Always use `--force-with-lease`, never `--force`.
- If the rebase produces more than 5 conflicting files in a single step, pause and ask the user whether to continue or abort.
- Do not skip verification after rebase.
- If verification fails and the fix is non-trivial, ask the user before amending.

$ARGUMENTS
