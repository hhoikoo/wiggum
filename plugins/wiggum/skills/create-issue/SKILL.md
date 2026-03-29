---
name: create-issue
description: Create a GitHub issue. Accepts structured input or free-text for interactive creation. Use when creating tickets programmatically or interactively.
argument-hint: "[-t <type>] [-s <summary>] [-b <body-file>] [-P <parent>] [-S <points>] [-l <label>]... [description]"
allowed-tools:
  - Bash(bash *)
  - Bash(gh *)
  - Bash(mkdir *)
  - Read
  - Glob
  - Grep
  - AskUserQuestion
  - Write
---

# Create Issue

Creates a GitHub issue. The body is applied at creation time.

## Issue Type Taxonomy

- **Epic**: large initiative spanning multiple issues
- **Story**: user-facing feature or behavior change
- **Bug**: defect or incorrect behavior
- **Task**: internal work, chore, refactoring, docs, CI, dependency updates

### GitHub Repo Name Detection

Always derive the repo name from git, never hardcode it:

```bash
basename "$(git remote get-url origin)" .git
```

### Assignee Detection

Get the current user's account ID:

```bash
gh api user --jq .login
```

## Workflow

### Phase 1: Parse Input

1. Parse `$ARGUMENTS` for structured flags. Supported flags:
   - `-t <type>`: Issue type (Epic, Story, Task, Bug)
   - `-s <summary>`: Issue title/summary
   - `-b <body-file>`: Path to markdown file with issue body
   - `-P <parent-key>`: Parent issue key (for sub-issues under an epic)
   - `-S <story-points>`: Story point estimate
   - `-l <label>`: Label (repeatable)
   - `-g <repo>`: GitHub repo name override

   If no flags are provided, treat the entire argument as a free-text description and proceed to Phase 2 (interactive mode).

### Phase 2: Interactive Mode (only if no structured flags)

2. If `$ARGUMENTS` is free text (no flags detected):
   a. Research the codebase to understand context: scan relevant modules, architecture, conventions.
   b. Present an initial assessment to the user.
   c. Use **AskUserQuestion** to clarify ambiguities and refine requirements.
   d. Propose an issue type classification with reasoning. Confirm with **AskUserQuestion**.
   e. Draft the issue body with sections: Summary, Description, Acceptance Criteria, Technical Notes.
   f. Present the draft and use **AskUserQuestion** to confirm or iterate.
   g. Once approved, write the body to a temp file and proceed to Phase 3 with the resolved type, summary, body file, and other fields.

### Phase 3: Create Issue

3. Prepare infrastructure: the temp directory is `/tmp/wiggum`. Run `mkdir -p` on it.

4. Create the issue (body is applied by the provider at creation time):
   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/issue-create.sh -t "<type>" -s "<summary>" [-b <body-file>] [-P <parent>] [-a <assignee>] [-S <points>] [-g <repo>] [-l <label>]...
   ```
   Read the created issue key from stdout.

5. Report the created issue key to the user.

## Rules

- Never create tickets without explicit user approval (in interactive mode).
- No AI attribution in titles or descriptions.
- No commit-style prefixes in issue titles (no `feat:`, `fix:`, etc.).
- Tests are part of implementation, not separate tickets.
- Each shell command must be a single, self-contained Bash tool call.
- Use AskUserQuestion for all confirmations in interactive mode.
- In structured mode (flags provided), create immediately without asking.

$ARGUMENTS
