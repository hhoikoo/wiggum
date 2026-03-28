---
name: review-feature-prd
description: Handle review comments on a PRD PR. Triages feedback, updates the PRD document, replies to threads, and pushes updates. Invoke manually when review comments arrive.
argument-hint: "<ticket-id>"
---

# Review Feature PRD

Handles review comments on a PRD pull request. Triages feedback with confidence scoring, delegates PRD updates to subagents, replies to threads, and pushes updates.

This skill is an **orchestrator**. The main context triages comments (lightweight) and coordinates subagents for heavy work (reading/updating the PRD, composing replies).

## Phase 1: Resolve PR

1. Parse `$ARGUMENTS` for the ticket ID.

2. Find the PR for this ticket's branch. The branch name follows the pattern `doc/prd-<ticket-id>`:
   ```bash
   gh pr list --head "doc/prd-$1" --json number,url --jq '.[0]'
   ```
   If no PR is found, report the error and stop.

3. Fetch all review comments on the PR:
   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/fetch-issue.sh <ticket-id>
   ```

   ```bash
   gh api repos/{owner}/{repo}/pulls/<pr-number>/comments --jq '.[] | {id, author: .user.login, body, path, line: .original_line, created_at}'
   ```

## Phase 2: Triage Comments

4. For each unresolved review comment, assign a confidence score (0-100%) representing how likely the comment identifies a real issue that should be addressed.

   **Human reviewers** (trust by default):
   - 50-100%: Incorporate the feedback.
   - 20-49%: Discuss -- reply explaining the current reasoning, ask for clarification.
   - 0-19%: Resolve with a brief explanation of why the current content is correct.

   **Bot/Copilot reviewers** (skeptical):
   - 70-100%: Incorporate the feedback.
   - 30-69%: Optional -- incorporate if trivial, otherwise resolve with explanation.
   - 0-29%: Resolve as spurious.

   Build a triage list: `[{id, author, body_excerpt, confidence, action}]` where action is one of `incorporate`, `discuss`, `resolve`.

## Phase 3: Apply Updates

5. For comments where action is `incorporate`: launch a subagent (or batch related comments into one subagent) to:
   - Read the current PRD from `.wiggum/specs/<ticket-id>/` on disk
   - Apply the requested change
   - Write the updated PRD back to disk
   - Return a short description of what changed

   The main context does **not** load the full PRD.

## Phase 4: Reply and Resolve

6. Launch a subagent to compose reply text for each comment based on the triage action:
   - `incorporate`: "Updated [section]. [Brief description of change]."
   - `discuss`: The reasoning for the current approach + a clarifying question.
   - `resolve`: Brief explanation of why the current content is correct.

7. Post replies to each comment:
   ```bash
   gh api repos/{owner}/{repo}/pulls/<pr-number>/comments/<comment-id>/replies -f body="<reply>"
   ```

8. Fetch unresolved review threads and resolve the ones that were addressed:
   ```bash
   bash $CLAUDE_PROJECT_DIR/.claude/scripts/pr-fetch-threads.sh <pr-number>
   bash $CLAUDE_PROJECT_DIR/.claude/scripts/pr-resolve-thread.sh <thread-id> [<thread-id>...]
   ```

## Phase 5: Commit and Report

9. If any PRD files were modified, commit and push. Delegate to `/commit`:
   - Format: `docs(<ticket-id>): address review feedback`

10. Print a summary table:

```
| Comment | Author | Confidence | Action | Status |
|---------|--------|-----------|--------|--------|
| <excerpt> | <author> | <score>% | <action> | <done/replied> |
```

## Rules

- This skill is stateless and idempotent. Safe to call repeatedly. Each invocation re-fetches all unresolved comments.
- The main context triages and coordinates. Subagents handle reading/writing the PRD and composing replies.
- Always delegate commits to the `/commit` skill.
- Always reply before resolving a thread -- every comment gets a response for audit trail.
- Do not ask the user for each comment decision. This skill is autonomous.

$ARGUMENTS
