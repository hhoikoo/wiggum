---
name: prd-review
description: Handle review comments on a PRD PR. Triages feedback, plans changes interactively with the user, updates the PRD document, replies to threads, and pushes updates. Invoke manually when review comments arrive.
argument-hint: "<ticket-id>"
---

# Review Feature PRD

Handles review comments on a PRD pull request. Triages feedback with confidence scoring, groups related comments into logical issues, plans changes with user approval, delegates PRD updates to subagents, replies to threads, and pushes updates.

This skill is an **orchestrator**. The main context triages and groups comments (lightweight) and coordinates subagents for heavy work (planning changes, reading/updating the PRD, composing replies). The planning phase is **interactive** -- the user approves proposed changes before they are applied.

## Phase 1: Resolve PR

1. Parse `$ARGUMENTS` for the ticket ID.

2. Find the PR for this ticket's branch. The branch name follows the pattern `doc/prd-<ticket-id>`:
   ```bash
   gh pr list --head "doc/prd-$1" --json number,url --jq '.[0]'
   ```
   If no PR is found, report the error and stop.

3. Fetch the issue context:
   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/fetch-issue.sh <ticket-id>
   ```

4. Fetch all review threads and their comments in a single GraphQL call. This returns both comment details and their parent thread IDs, which are needed for thread resolution later:

   ```bash
   gh api graphql \
     -F owner="$(gh repo view --json owner --jq '.owner.login')" \
     -F name="$(gh repo view --json name --jq '.name')" \
     -F number=<pr-number> \
     -f query='
   query($owner: String!, $name: String!, $number: Int!) {
     repository(owner: $owner, name: $name) {
       pullRequest(number: $number) {
         reviewThreads(first: 100) {
           nodes {
             id
             isResolved
             comments(first: 50) {
               nodes {
                 databaseId
                 author { login }
                 body
                 path
                 originalLine
                 createdAt
               }
             }
           }
         }
       }
     }
   }'
   ```

   Filter to unresolved threads only. For each unresolved thread, extract: `thread_id`, and for each comment: `comment_id` (databaseId), `author`, `body`, `path`, `line`.

## Phase 2: Triage Comments

5. For each unresolved review comment, assign a confidence score (0-100%) representing how likely the comment identifies a real issue that should be addressed.

   **Human reviewers** (trust by default):
   - 50-100%: Incorporate the feedback.
   - 20-49%: Discuss -- reply explaining the current reasoning, ask for clarification.
   - 0-19%: Resolve with a brief explanation of why the current content is correct.

   **Bot/Copilot reviewers** (skeptical):
   - 70-100%: Incorporate the feedback.
   - 30-69%: Optional -- incorporate if trivial, otherwise resolve with explanation.
   - 0-29%: Resolve as spurious.

   Build a triage list: `[{comment_id, thread_id, author, body_excerpt, confidence, action}]` where action is one of `incorporate`, `discuss`, `resolve`.

## Phase 3: Group Issues

6. Group all `incorporate` comments into logical issue groups. Comments do not map 1:1 to issues:
   - Multiple comments pointing at the same underlying problem become one group
   - A single comment raising multiple distinct issues gets split across groups
   - Use judgment to determine the right grouping

   Each group gets:
   - A short label (e.g., "missing error handling section", "scope creep in non-goals")
   - The set of `{comment_id, thread_id}` pairs it addresses
   - A 1-sentence description of the issue

   `discuss` and `resolve` comments skip grouping -- they are handled autonomously in Phase 7.

## Phase 4: Plan

7. Launch one **read-only** planning agent per issue group in a **single message** for parallel execution. Each agent:
   - Reads the current PRD from `.wiggum/specs/<ticket-id>/` on disk
   - Receives the relevant comment bodies in its prompt
   - Returns a plan: which sections to change, what the change would be, and why
   - Does **not** modify any files

   The main context collects the plan summaries. Do not load the full PRD into the main context.

## Phase 5: Interactive Review

8. Present all plans to the user:

   ```
   Group 1: <label>
     Comments: #<id>, #<id>
     Plan: <summary of proposed change>

   Group 2: <label>
     Comments: #<id>
     Plan: <summary of proposed change>
   ```

9. Use **AskUserQuestion** to get feedback. The user can:
   - Approve all plans
   - Request changes to specific groups
   - Reject specific groups (downgrade their comments to `resolve` action)
   - Ask follow-up questions

10. If the user requests changes to specific groups, re-launch those planning agents with the user's feedback appended to the prompt. Present updated plans and ask again. Repeat until the user approves.

## Phase 6: Apply Updates

11. For each approved issue group: launch a subagent to:
    - Read the current PRD from `.wiggum/specs/<ticket-id>/` on disk
    - Apply the change described in the approved plan
    - Write the updated PRD back to disk
    - Return a short description of what changed

    Pass the **approved plan** to the subagent so the change is targeted. The main context does **not** load the full PRD.

## Phase 7: Reply and Resolve

12. Launch a subagent to compose reply text for each comment based on the triage action:
    - `incorporate`: "Updated [section]. [Brief description of change]."
    - `discuss`: The reasoning for the current approach + a clarifying question.
    - `resolve`: Brief explanation of why the current content is correct.

13. Post replies to each comment:
    ```bash
    gh api repos/{owner}/{repo}/pulls/<pr-number>/comments/<comment-id>/replies -f body="<reply>"
    ```

14. Resolve threads for `incorporate` and `resolve` comments using the thread IDs captured in Phase 1. `discuss` threads stay open (awaiting human response).
    ```bash
    gh api graphql -F threadId="<thread-id>" -f query='
    mutation($threadId: ID!) {
      resolveReviewThread(input: {threadId: $threadId}) {
        thread { isResolved }
      }
    }'
    ```

## Phase 8: Commit and Report

15. If any PRD files were modified, commit and push. Delegate to `/wiggum:commit`:
    - Format: `docs(<ticket-id>): address review feedback`

16. Print a summary table:

```
| Comment | Author | Confidence | Action | Group | Status |
|---------|--------|-----------|--------|-------|--------|
| <excerpt> | <author> | <score>% | <action> | <group-label or -> | <done/replied> |
```

## Rules

- This skill is stateless and idempotent. Safe to call repeatedly. Each invocation re-fetches all unresolved comments.
- The main context triages, groups, and coordinates. Subagents handle planning, reading/writing the PRD, and composing replies.
- The planning phase (Phases 4-5) is interactive. `discuss` and `resolve` comments are handled autonomously without user input.
- Thread resolution applies to `incorporate` (after applying changes) and `resolve` (after replying) comments. `discuss` threads stay open.
- Always delegate commits to the `/wiggum:commit` skill.
- Always reply before resolving a thread -- every comment gets a response for audit trail.

$ARGUMENTS
