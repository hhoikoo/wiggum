---
name: create-branch
description: Create a correctly named branch and check it out. Use when starting work on a ticket or a quick fix and you need a branch.
argument-hint: "<ticket-id> or type: description"
allowed-tools:
  - Bash(bash *)
  - Bash(git *)
  - Bash(gh *)
---

# Create Branch

Create a branch and check it out. Supports two modes: ticket-based (with ticket ID) and description-based (for quick fixes without a ticket).

## Step 0: Resolve default branch and sync

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/setup-branch.sh
```

Parse the JSON output: `base_branch` is the default branch, `current_branch` is where you are, `merged` indicates if upstream changes were integrated.

If `current_branch` is not `base_branch`, stop and ask the user how to proceed:
- Continue and branch from the current branch.
- Switch to the default branch first, then create the new branch.
- Switch to a different branch the user specifies.

## Usage

`$ARGUMENTS` contains either:
- A ticket ID (e.g., `<ticket-id>`) -- fetches ticket details to derive the branch name.
- A type and description (e.g., `chore: update skill rules`) -- derives the branch name directly.

If `$ARGUMENTS` starts with a number (GitHub issue number, e.g., `42`), use **ticket mode**. Otherwise, use **description mode**.

## Workflow

### Step 1: Determine type and short-name

**Ticket mode** (argument matches `<ticket-id>`):

1. Fetch ticket details:
   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/issue-view.sh <ticket-id>
   ```
2. Determine the commit type prefix. Use the issue type mappings below, starting from the issue type's `commit_type`, then refine using the ticket title and the inference table.
   Issue type to commit type mapping:
   - Epic -> `feat`
   - Story -> `feat`
   - Bug -> `fix`
   - Task -> infer from title keywords: "add/create/implement" -> `feat`, "fix/resolve/correct" -> `fix`, "refactor/clean/simplify" -> `refactor`, "test" -> `test`, "doc/readme" -> `docs`, "update dep/upgrade/bump" -> `deps`
   - If the issue type has a clear mapping (e.g., Bug -> `fix`, Story -> `feat`), use it.
   - If the issue type is Task or ambiguous, infer from the ticket title using the keyword table above.
   - If still ambiguous, ask the user.
3. Extract 2-4 key words from the ticket title for the short-name.

**Description mode** (argument is `<type>: <description>`):

1. Parse the type prefix before the colon. It must be one of: `feat`, `fix`, `doc`, `docs`, `refactor`, `test`, `perf`, `ci`, `chore`, `deps`, `release`.
2. Extract 2-4 key words from the description for the short-name.

For both modes, convert the short-name to kebab-case, lowercase, stripping filler words (the, a, an, is, for, to, in, on, with).

### Step 2: Create and checkout branch

**Ticket mode:**
```bash
git checkout -b <type>/<ticket-id>/<short-name>
```

**Description mode:**
```bash
git checkout -b <type>/<short-name>
```

### Step 3: Report

Print the branch name and a one-line summary.

## Branch Naming Convention

Format: `<type>/<ticket-id>/<short-name>` (ticket mode) or `<type>/<short-name>` (description mode).

- `<type>`: one of `feat`, `fix`, `doc`, `docs`, `refactor`, `test`, `perf`, `ci`, `chore`, `deps`, `release`
- `<ticket-id>`: GitHub issue number (e.g., `42`)
- `<short-name>`: 2-4 kebab-case words derived from the title, stripped of filler words
- All lowercase, no spaces, no special characters beyond hyphens and slashes

$ARGUMENTS
