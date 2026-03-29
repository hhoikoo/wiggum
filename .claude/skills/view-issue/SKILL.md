---
name: view-issue
description: View issue details. Use when looking up a ticket's title, description, status, and other metadata.
argument-hint: "<issue-key>"
allowed-tools:
  - Bash(bash *)
---

# View Issue

Fetch and display the details of an issue.

## Workflow

1. Fetch the issue:
   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/issue-view.sh $ARGUMENTS
   ```
2. Parse the returned JSON fields: `key`, `summary`, `description`, `type`, `status`, `parent`.
3. Print the issue details in a readable format:
   - **Key**: the issue key
   - **Summary**: the title
   - **Type**: issue type
   - **Status**: current status
   - **Parent**: parent issue key (omit if empty)
   - **Description**: full description body

$ARGUMENTS
