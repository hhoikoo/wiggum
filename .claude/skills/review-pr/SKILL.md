---
name: review-pr
description: Review and address PR feedback. Use when review comments come in on a PR. Fetches review comments, triages them with confidence scoring, fixes valid issues, and resolves threads.
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

# Review PR

Address review comments on a pull request.

## Workflow

### 1. Find the PR

- If `$ARGUMENTS` contains a PR number, use it.
- Otherwise, detect from the current branch: `gh pr view --json number,url`

### 2. Fetch Review Comments

```bash
.claude/scripts/pr-fetch-comments.sh {number}
```

### 3. Triage Each Comment

Assign a confidence score (0-100%) that the comment identifies a real issue.

**Human reviewers** -- trust by default:
- 50-100%: Fix it.
- 20-49%: Discuss -- reply explaining your reasoning, ask for clarification.
- 0-19%: Resolve with a brief explanation of why the current code is correct.

**Bot/Copilot reviewers** -- skeptical:
- 70-100%: Fix it.
- 30-69%: Optional -- fix if trivial, otherwise resolve with explanation.
- 0-29%: Resolve as spurious.

### 4. Fix Valid Issues

- Make the code changes.
- Run `uv run pre-commit run --all-files` to verify the fix.
- Commit using the `/commit` skill (MUST delegate, never commit directly).
- Group related fixes into a single commit when they address the same concern.

### 5. Reply and Resolve Threads

Reply to each comment using the GitHub API:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments/{comment_id}/replies -f body="<response>"
```

Fetch unresolved thread IDs, then resolve them:

```bash
.claude/scripts/pr-fetch-threads.sh {number}
.claude/scripts/pr-resolve-thread.sh {thread_id} [{thread_id}...]
```

### 6. Output Summary

Print a table:

| Comment | Author | Confidence | Action | Status |
|---------|--------|------------|--------|--------|

## Rules

- Always delegate commits to the `/commit` skill.
- No AI attribution in replies or commits.
- When disagreeing with a comment, be direct but respectful. Cite specific code or docs.

$ARGUMENTS
