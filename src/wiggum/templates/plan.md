# Planning Phase

You are planning the implementation of ticket **$issue_id**.

## Specs

$specs_content

## Instructions

1. Read the specs above carefully and understand the requirements.
2. Examine the codebase to identify files that need to be created or modified.
3. Write a detailed implementation plan as a numbered checklist in `$impl_path/IMPLEMENTATION_PLAN.md`.
4. Each step should be a concrete, actionable task (one checkbox per task).
5. Order steps by dependency -- earlier steps should not depend on later ones.
6. Every task must require a complete, working implementation. Never plan a task as "create skeleton", "add stub", or "scaffold" -- plan the real logic from the start.

## Task Sizing

Each task must be completable in a single build iteration (one context window). If a task cannot be described in 2-3 sentences, split it.

Right-sized tasks:
- Add a pydantic model and its tests
- Implement a single CLI subcommand
- Add a utility function with edge-case handling

Too large (split these):
- "Build the entire feature" -- split into model, logic, CLI, tests
- "Add the API layer" -- split into one task per endpoint or handler
- "Refactor the module" -- split into one task per concern

## Task Ordering

Tasks execute in priority order. Earlier tasks must not depend on later ones.

Correct order:
1. Data models and configuration
2. Core logic and utilities
3. Integration points (CLI, API, etc.)
4. Tests that exercise the integration

## Acceptance Criteria

Each task's description must include verifiable acceptance criteria -- things the build agent can check, not vague goals.

Good: "Add `status` field to Config with default 'pending'; pyright passes"
Bad: "Works correctly", "Handles edge cases"

Always include "quality checks pass" (typecheck, lint, tests) as an implicit criterion.

## Completion Signal

When the plan is complete, output a fenced JSON block with the status:

```json
{"status": "complete"}
```

If you need another iteration to refine the plan, output:

```json
{"status": "in_progress"}
```
