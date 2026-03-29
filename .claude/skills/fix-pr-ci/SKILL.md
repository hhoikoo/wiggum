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
  - Bash(bash *)
  - Bash(gh *)
  - "Bash(uv run pre-commit run --all-files)"
---

# Fix CI

Diagnose and fix CI failures on the current PR or branch.

## Workflow

### 1. Fetch Failing Checks

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/fetch-failing-checks.sh $ARGUMENTS
```

Parse the JSON output. If empty (`[]`), all checks pass -- report success and stop. Otherwise proceed with the list of failures, each containing `name`, `conclusion`, `log_url`, and `log_excerpt`.

### 2. Diagnose

Read the failure logs from the script output and categorize each failure:

- **Lint** -- linter errors. Read the project's linter config and the flagged files to understand context.
- **Build** -- compilation or Docker build errors. Read the project's dependency manifest, `Dockerfile`, and the failing source files.
- **Test** -- test failures. Read the failing test file and the source code it exercises.
- **Workflow** -- CI pipeline configuration errors. Read the workflow YAML.

### 3. Fix

- Apply the minimal fix for each failure.
- Run `uv run pre-commit run --all-files` locally to verify the fix before pushing.
- If verification fails, iterate until it passes.

### 4. Commit and Push

- Invoke the `/wiggum:commit` skill. The `/wiggum:commit` skill handles pushing when a PR exists.

### 5. Verify

- Wait for CI to start: `gh run list --branch <current-branch> --limit 1`.
- Report which checks were failing and what was fixed.

## Rules

- Do not skip local verification (`uv run pre-commit run --all-files`) before pushing.
- One commit per logical fix. If lint and test failures are unrelated, separate the commits.
- If a failure is not caused by code on this branch (flaky test, infrastructure issue), report it instead of attempting a fix.

$ARGUMENTS
