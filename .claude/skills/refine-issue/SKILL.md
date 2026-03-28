---
name: refine-issue
description: Refine an existing ticket for AI consumption. Rewrites the summary and description to be detailed, structured, and actionable. Use when an existing ticket needs a better description before implementation.
argument-hint: "ISSUE_KEY"
allowed-tools:
  - Bash($CLAUDE_PROJECT_DIR/.claude/scripts/*.sh)
  - Bash($CLAUDE_PROJECT_DIR/.claude/scripts/*.sh *)
  - Bash(mkdir *)
  - Bash(uuidgen*)
  - Read
  - Glob
  - Grep
  - WebSearch
  - WebFetch
  - AskUserQuestion
  - Write
---

# Refine Issue

Takes an existing ticket and rewrites its summary and description so it is detailed, structured, and ready for AI-driven implementation. The original ticket may be vague, incomplete, or written in a style that doesn't translate well to actionable work items.

## Workflow

### Phase 1: Read and Research

1. Fetch the existing ticket using:
   ```bash
   .claude/scripts/issue-view.sh ISSUE_KEY
   ```
   Extract the current summary, description, issue type, status, and any linked issues.
2. Research the codebase: scan relevant modules, architecture, conventions, and dependencies based on what the ticket describes. Use Glob, Grep, Read to understand the affected areas.
3. If the ticket references external libraries, APIs, or concepts that need verification, use WebSearch/WebFetch.

### Phase 2: Interactive Refinement

4. Present the current ticket state to the user: summary, description, type, and your initial understanding of what the ticket is asking for.
5. Use the **AskUserQuestion** tool to ask clarifying questions. Focus on:
   - Ambiguities in the original description
   - Missing acceptance criteria or scope boundaries
   - Unstated assumptions about behavior or architecture
   - Whether the user wants to change the scope or direction
6. Iterate using AskUserQuestion until the requirements are fully understood. The user can provide additional context, redirect scope, or answer questions at each step.

### Phase 3: Rewrite and Confirm

7. Generate the refined ticket content with structured sections:
   - **Summary**: Concise one-line title (may differ from the original if it was unclear).
   - **Description**: Detailed explanation of the work, context, motivation, and background. Include relevant code paths, module names, and architectural context discovered during research.
   - **Acceptance Criteria**: Clear, testable criteria for what "done" looks like.
   - **Technical Notes**: Affected modules, implementation hints, dependencies, edge cases, and anything the implementer needs to know.
8. Present the refined summary and description to the user. Show a diff-style comparison against the original so the user can see what changed.
9. Use **AskUserQuestion** to confirm the update or gather further edits. Keep iterating until the user approves.

### Phase 4: Update

10. Write the refined English description to a temp file: the temp directory is `/tmp/wiggum`. Run `mkdir -p` on it. Use `uuidgen` to produce `<tempDir>/issue-body-<uuid>.md`. Write the description using the **Write** tool.

11. Update the ticket:
    ```bash
    .claude/scripts/issue-edit.sh ISSUE_KEY -s "<refined-summary>" -b <body-file>
    ```
    If only the description changed (summary is fine), omit `-s`.

12. Report the updated ticket key and URL to the user.

## Rules

- Never update a ticket without explicit user approval.
- No AI attribution in ticket titles or descriptions.
- If the existing summary contains a commit-style type prefix (`feat:`, `fix:`, etc.), remove it.
- Preserve the original ticket type -- this skill refines content, not classification.
- Do not modify any fields other than summary and description (no status, assignee, priority, sprint, or custom field changes).
- Use AskUserQuestion for all clarification and confirmation steps. Do not guess or assume when the original description is ambiguous.
- Tests are part of the implementation, not a separate concern. Acceptance criteria should reflect this.

$ARGUMENTS
