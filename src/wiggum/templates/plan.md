# Planning Phase

You are planning the implementation of ticket **$issue_id**.

## Specs

$specs_content

## Instructions

1. Read the specs above carefully and understand the requirements.
2. Examine the codebase to identify files that need to be created or modified.
3. Write a detailed implementation plan as a numbered checklist in IMPLEMENTATION_PLAN.md.
4. Each step should be a concrete, actionable task (one checkbox per task).
5. Order steps by dependency -- earlier steps should not depend on later ones.
6. Every task must require a complete, working implementation. Never plan a task as "create skeleton", "add stub", or "scaffold" -- plan the real logic from the start.

## Completion Signal

When the plan is complete, output a fenced JSON block with the status:

```json
{"status": "complete"}
```

If you need another iteration to refine the plan, output:

```json
{"status": "in_progress"}
```
