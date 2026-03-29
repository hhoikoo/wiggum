---
name: prd-create
description: Given a proposal ticket, research the codebase and web, draft a PRD document, iterate on feedback, and create a PR. Designed to run in a spawned tmux session with --dangerously-skip-permissions.
argument-hint: "<ticket-id>"
---

# Create Feature PRD

Autonomous PRD generation skill. Runs in a spawned tmux session. Performs massive parallel research, drafts a structured PRD, iterates with the user on open questions, and creates a PR.

This skill produces a **proposal**, not an implementation. The ticket it receives is a proposal ticket that resolves when the PRD pull request merges. A separate implementation ticket is created downstream from the approved PRD. All outputs -- research documents, the PRD itself, the PR description -- should be framed as defining requirements and design, not as implementing a feature.

This skill is an **orchestrator**. It coordinates subagents but keeps its own context clean. Heavy content (raw research, full PRD text, section edits) lives on disk and is read by subagents, not loaded into the main context.

## Phase 1: Load Context

1. Parse `$ARGUMENTS` for the ticket ID.

2. Fetch the issue body:
   ```bash
   bash ${CLAUDE_SKILL_DIR}/scripts/fetch-issue.sh <ticket-id>
   ```
   Store the `summary` and `description` fields. This is the polished feature summary from `/wiggum:feature-propose`.

3. Read the project's CLAUDE.md and directory structure to understand the codebase context.

## Phase 2: Parallel Research

4. Analyze the feature description to identify research axes:
   - **N codebase aspects** to investigate (e.g., "How does the config system work?", "What interfaces exist for X?")
   - **M external repos** to study (if the feature references sibling projects)
   - **K online topics** to research (e.g., best practices, reference implementations, standards)

5. Launch **all** research agents in a **single message** for maximum parallelism:
   - N `codebase-researcher` agents -- one per codebase aspect, each with a focused question
   - M `cross-project-researcher` agents -- one per external repo + question
   - K `web-researcher` agents -- one per online topic
   - All agents are read-only

6. Collect the short summaries returned by each agent. Do not request or load the full research content into this context.

## Phase 3: Store Research

7. Create the research directory:
   ```bash
   mkdir -p .wiggum/specs/<ticket-id>/research
   ```

8. Each research agent should write its findings directly to a per-source file in `.wiggum/specs/<ticket-id>/research/<hash>-<semantic-name>.md`. Instruct agents to write their output to disk, and return only a 2-3 sentence summary to the main context.

   The `<hash>` is the first 8 characters of a SHA-256 hash of the sanitized research query (for dedup). The `<semantic-name>` is a kebab-case descriptor.

9. Launch a `codebase-researcher` subagent to read all per-source files in `.wiggum/specs/<ticket-id>/research/` and synthesize them into `.wiggum/specs/<ticket-id>/research/RESEARCH.md` -- the executive research summary. The main context receives only the summary text, not the raw research.

## Phase 4: Draft PRD

10. Launch a `prd-writer` subagent with:
    - The feature description (from the ticket)
    - The executive research summary (from RESEARCH.md)
    - The ticket ID and short name

    The agent writes the PRD directly to `.wiggum/specs/<ticket-id>/<short-name>.md`. It returns a summary of what was written plus the list of open questions.

    PRD structure:
    - Summary (problem + solution + tradeoff, mechanics, why-this-over-alternatives)
    - Goals / Non-Goals
    - Architecture (Mermaid diagram)
    - Design Decisions (numbered, with rationale)
    - Required Changes (table: Component | Change)
    - Acceptance Tests (checkbox Given/When/Then format)
    - Implementation Sketch (phases, not tickets)
    - Alternatives Considered (comparison table)
    - Open Questions

11. Store the PRD summary and open questions in this context. Do not load the full PRD.

## Phase 5: Interactive Refinement

12. Present to the user:
    - The recommended approach and key design decisions (from the prd-writer summary)
    - Open questions that need human input

13. Use **AskUserQuestion** to get feedback on open questions. Batch related questions (up to 4 per call).

14. For each round of feedback: launch a subagent to read the PRD from disk, apply updates based on the feedback, and write it back. The main context does not hold the full PRD content.

15. Ask for final approval only after all open questions are resolved.

## Phase 6: Create PR

16. Commit the PRD and research docs. Delegate to `/wiggum:commit`:
    - Format: `docs(<ticket-id>): <feature-name>`

17. Push and create PR. Delegate to `/wiggum:create-pr`:
    - Title: `docs(<ticket-id>): <feature-name>`
    - Body: frame as a proposal -- "PRD for <feature>", followed by the executive summary and a link to the PRD file in the repo. Do not use implementation language ("this PR implements...").
    - Link PR to the tracking issue

18. For each unresolved open question remaining in the PRD, post it as a separate review comment on the PR so reviewers can address them.

## Rules

- This skill is an orchestrator. Never load full research or full PRD text into the main context. Always delegate to subagents for reading and writing heavy content.
- All research agents must be launched in a single message for parallel execution.
- Each subagent gets a focused, self-contained task. Do not pass the entire conversation history.
- Always delegate commits to the `/wiggum:commit` skill and PR creation to the `/wiggum:create-pr` skill.
- If a research agent fails, log the failure and continue with the remaining results. Do not retry.

$ARGUMENTS
