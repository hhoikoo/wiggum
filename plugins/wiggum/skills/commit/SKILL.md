---
name: commit
description: Create git commits following project conventional commit standards. Use when preparing commits, writing commit messages, or committing staged changes.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(git *)
  - Bash(gh *)
  - Bash(bash *)
---

# Commit

Create a git commit following this project's conventions.

## Conventions

Follow conventional commit format: `<type>(<scope>): <description>` or `<type>: <description>`.

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`, `deps`.

Rules:
- Subject line: imperative mood, lowercase, no period, max 72 characters.
- Scope is optional. Use the module or area being changed (e.g., `feat(auth): add login endpoint`).
- Body: separated by blank line, explains *why* not *what*. Wrap at 72 characters.
- Footer: `Resolves #<issue>` or `Breaking change:` if applicable.
- One logical change per commit.

## Workflow

1. Run `git status` and `git diff` (staged + unstaged) to understand the current state.
2. Run `git log --oneline -5` to see recent commit style for consistency.
3. If nothing is staged, identify and stage the relevant files. Ask the user if the scope is unclear.
4. Draft a commit message following the conventions above.
5. Create the commit.
6. If pre-commit hooks fail: read the hook output, fix the issues, re-stage, and create a new commit. Do not use `--no-verify`.
7. Run `git status` to verify success.
8. Print the full commit message to the user.
9. **Push or prompt:**
   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/check-push-status.sh
   ```
   If `pushed` is true, report. If `has_remote` is false, tell the user to run the `/wiggum:create-pr` skill when ready.
10. **Documentation check:**
    - Check if a PR exists for the current branch: `gh pr view --json number 2>/dev/null`.
    - If no PR exists yet, skip this step -- the documentation check will run as part of the `/wiggum:create-pr` skill when the PR is created.
    - If a PR exists, resolve the base branch:
      ```bash
      bash ${CLAUDE_SKILL_DIR}/scripts/resolve-base-branch.sh
      ```
      Then run `git diff <base>...HEAD --stat` and `git diff <base>...HEAD` to understand the full scope of changes.
    - Determine whether updates are needed to README, CLAUDE.md, inline docs, or other developer-facing documentation. Consider: new public APIs, changed behavior, architectural shifts, new dependencies, or changes to hooks/skills/agents/config. Internal refactors, test additions, and bug fixes that restore documented behavior do not warrant doc updates.
    - If documentation changes are recommended, present each to the user via AskUserQuestion (approve/reject) and apply only the approved edits.
    - If updates are needed, apply them, commit (following project commit conventions), and push.
    - **Skip if already run recently:** If a documentation check has already been performed earlier in the same pipeline run (e.g., during `quick-push`), skip this step. The `/wiggum:create-pr` skill will run the final documentation check.

$ARGUMENTS
