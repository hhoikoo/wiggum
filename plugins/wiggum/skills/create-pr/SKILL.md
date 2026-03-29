---
name: create-pr
description: Create a pull request following project conventions. Use when the branch is ready for review. Pushes the branch, generates a PR title and body from branch and commit history, and opens a PR.
argument-hint: "[--no-review]"
allowed-tools:
  - Agent
  - Bash(bash *)
  - Bash(gh *)
  - Bash(git *)
  - Bash(mktemp*)
---

# Create PR

Create a pull request following project conventions.

## Workflow

0. **Resolve base branch:**

   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/resolve-base-branch.sh
   ```

   Use the output as `<base>` throughout this skill.

1. **Gather state:**
   - `git status` to verify clean working tree (warn if uncommitted changes exist).
   - `git log <base>..HEAD --oneline` to see all commits on this branch.
   - `git diff <base>...HEAD --stat` to see the file-level summary of changes.

2. **Push branch:**

   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/push-branch.sh
   ```

3. **Generate PR title:**
   - Follow the same format as commit subject lines from `/wiggum:commit`: `<type>(<ticket-id>): <short description>` or `<type>: <short description>`.
   - Derive the type from the branch prefix (e.g., `feat/42/add-state-machine` -> `feat`).
   - Extract the ticket ID from the branch name if present (e.g., `feat/<ticket-id>/add-widget` -> `<ticket-id>`).
   - Derive the description from the branch short-name or commit messages. Capitalize first letter, no period, imperative mood.

4. **Generate PR body:**
   - Launch a general-purpose subagent via the Agent tool. Pass: base branch name, current branch name, commit log (`git log <base>..HEAD --oneline`), and diff stat (`git diff <base>...HEAD --stat`). Subagent instructions:
     1. Read `.github/PULL_REQUEST_TEMPLATE.md` for the template structure.
     2. If `.github/PULL_REQUEST_TEMPLATE.md` exists, use it as the template structure. If not, use a standard format with Summary, Changes, and Test Plan sections.
     3. Run `git diff <base>...HEAD` to get the full diff. Read relevant source files if needed for accurate descriptions.
     4. Extract the ticket ID from the branch name if present and include a ticket reference following the convention format.
     5. Fill every section of the template following the rules in the convention file. Copy checklist items character-for-character -- only change `[ ]` to `[x]`. Strip HTML comments. Preserve fixed sections verbatim.
     6. Run `mkdir -p /tmp/wiggum`, then write the body to `/tmp/wiggum/pr-body-$(uuidgen).md`.
     7. Return the temp file path.

5. **Create the PR:**
   `gh pr create --title "<title>" --body-file <temp-path> --assignee @me --base <base>`

5a. **Link issue to PR:**
   - If a ticket ID was resolved in step 0:
     1. Wait 15 seconds (gives `pr-issue-link.yml` CI workflow time to run first).
     2. Call as backup -- if CI already linked it, the script exits cleanly; if not, it appends the reference:
        ```bash
        bash ${CLAUDE_SKILL_DIR}/scripts/pr-link-issue.sh <pr-number> <ticket-id>
        ```

6. **Request reviews:**
   - **Skip this step** if `$ARGUMENTS` contains `--no-review`.
   - Ask the user which GitHub usernames to request review from. If the user does not specify any, skip this step.
   - Request review from each resolved reviewer:
     ```bash
     gh pr edit --add-reviewer <reviewer1>
     ```

7. **Documentation check:**
   - Run `git diff <base>...HEAD --stat` and `git diff <base>...HEAD` to understand the full scope of changes.
   - Determine whether updates are needed to README, CLAUDE.md, inline docs, or other developer-facing documentation. Consider: new public APIs, changed behavior, architectural shifts, new dependencies, or changes to hooks/skills/agents/config. Internal refactors, test additions, and bug fixes that restore documented behavior do not warrant doc updates.
   - If documentation changes are recommended, present each to the user via AskUserQuestion (approve/reject) and apply only the approved edits.
   - If updates are needed, apply them, commit (following project commit conventions), and push before reporting.
   - **Skip if already run recently:** If a documentation check was already performed on the same set of commits earlier in this pipeline run (e.g., by the `/wiggum:commit` skill), skip this step.

8. **Report:**
   ```
   =========================================================================
   PR CREATED - AWAITING REVIEW
   =========================================================================

   PR: <PR URL>
   Branch: <branch name>
   Ticket: <ticket-id> (or "none")

   Summary:
   - <what was implemented>

   Status:
   - Reviews requested: <list of reviewers> (or SKIPPED)

   =========================================================================
   Awaiting review feedback.
   =========================================================================
   ```

## Rules

- No AI attribution anywhere in the PR title or body.
- PR title follows commit-conventions format exactly.
- PR body must match the template structure -- GitHub Actions workflows depend on it.

$ARGUMENTS
