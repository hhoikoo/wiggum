---
name: fix-pr-ci
description: Diagnose and fix CI failures on the current branch. Use when CI checks are failing on a PR. Fetches failing check logs, identifies root causes, applies fixes, and pushes.
argument-hint: "[PR number]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Skill
  - Bash($CLAUDE_PROJECT_DIR/.claude/scripts/*.sh)
  - Bash($CLAUDE_PROJECT_DIR/.claude/scripts/*.sh *)
  - Bash(gh *)
  - "Bash(uv run pre-commit run --all-files)"
---

# Fix CI

Diagnose and fix CI failures on the current PR or branch.

## Workflow

### 1. Identify Failing Checks

- If `$ARGUMENTS` contains a PR number, use it. Otherwise detect from the current branch: `gh pr view --json number`
- List check status: `gh pr checks`
- If all checks pass, report success and stop.

### 2. Fetch Failure Logs

For each failing check:

```bash
gh run view --log-failed <run-id>
```

If the log is too large, focus on the last 200 lines of the failing job step.

### 3. Diagnose

Read the failure logs and categorize the failure:

- **Lint** -- linter errors. Read the project's linter config and the flagged files to understand context.
- **Build** -- compilation or Docker build errors. Read the project's dependency manifest, `Dockerfile`, and the failing source files.
- **Test** -- test failures. Read the failing test file and the source code it exercises.
- **Workflow** -- CI pipeline configuration errors. Read the workflow YAML.

### 4. Fix

- Apply the minimal fix for each failure.
- Run `uv run pre-commit run --all-files` locally to verify the fix before pushing.
- If verification fails, iterate until it passes.

### 5. Commit and Push

- Invoke the `/commit` skill. The `/commit` skill handles pushing when a PR exists.

### 6. Verify

- Wait for CI to start: `gh run list --branch <current-branch> --limit 1` (substitute the current branch name).
- Report which checks were failing and what was fixed.

## Rules

- Do not skip local verification (`uv run pre-commit run --all-files`) before pushing.
- One commit per logical fix. If lint and test failures are unrelated, separate the commits.
- If a failure is not caused by code on this branch (flaky test, infrastructure issue), report it instead of attempting a fix.

$ARGUMENTS
