---
name: feature-propose
description: Interactively draft a feature proposal and spawn a background PRD generation session. Use when starting a new feature or significant change.
argument-hint: "[feature description in plain English]"
---

# Propose Feature

Takes a rough feature idea, polishes it through brief conversation, creates a tracking ticket, and spawns a background Claude session to generate the PRD.

## Phase 1: Gather & Polish Feature Description

Read `$ARGUMENTS` as the initial feature idea. If the description is vague or incomplete, ask the user conversationally to clarify:

- What problem does this solve?
- Who benefits? Any constraints or non-goals?
- Key acceptance criteria?

Keep the back-and-forth brief -- 2-3 rounds max. Produce a polished feature summary: a concise paragraph describing the feature, its motivation, and its scope. This summary will be the body of the tracking ticket and the input to PRD generation.

**Framing**: The summary describes what needs to be specified, not how to implement it. Write from the perspective of "what should the PRD cover?" -- motivation, scope boundaries, key questions to resolve. Do not include implementation details, acceptance criteria, CLI signatures, or architecture decisions; those belong in the PRD itself. Never reference local file paths or machine-specific resources; the issue must be self-contained and readable by anyone.

## Phase 2: Create Tracking Ticket

Delegate to the `/wiggum:create-issue` skill to create a GitHub issue:

- **Type**: Task (this is a proposal document, not an implementation ticket)
- **Title**: `Proposal: <feature name>` -- concise feature name, no implementation verbs
- **Body**: the polished feature summary from Phase 1

This ticket tracks the *proposal*, not the implementation. It resolves when the PRD pull request merges. A separate implementation ticket is created downstream from the approved PRD.

Capture the issue number from the skill output.

## Phase 3: Spawn Background PRD Session

Launch a background Claude session in tmux to generate the PRD autonomously:

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/session-launch.sh \
  --ticket-id <ticket-id> \
  --repo-path "$(git rev-parse --show-toplevel)" \
  --base-branch main \
  --command "/wiggum:prd-create <ticket-id>"
```

If the script fails, report the error and stop. Do not retry.

## Phase 4: Report

Print a summary for the user:

```
Proposal ticket created: #<number> - <title>

PRD generation started in background:
  tmux session:   wiggum-<repo-name>
  tmux window:    <ticket-id>
  worktree:       .wiggum/worktrees/<ticket-id>/

To watch progress:
  tmux attach -t wiggum-<repo-name>

The session will create a PR with the PRD when ready.
```

## Rules

- Do not use AskUserQuestion for the initial feature description. Use plain conversational text.
- Do not skip Phase 1 even if the user provides a detailed description. At minimum, confirm the scope.
- Always delegate issue creation to the `/wiggum:create-issue` skill. Never create issues directly.
- The spawned session runs independently. Do not wait for it to complete.

$ARGUMENTS
