# Build Phase

You are implementing ticket **$issue_id**.

## Current Task

$task_description

## Before You Start

1. Read the Codebase Patterns section at the top of PROGRESS.md (if it exists). Previous iterations may have recorded patterns and gotchas that apply to your work.

## Instructions

1. Implement the task described above with **complete, working code**.
2. Follow existing code patterns and conventions.
3. Write tests for any new functionality.
$quality_section
5. Do NOT commit broken code. If quality checks fail, fix the issues before committing.
6. Commit your changes using the /commit skill.
7. Update PROGRESS.md with what you accomplished (see format below).
8. Update nearby CLAUDE.md files if you discovered reusable patterns (see guidance below).

## Implementation Requirements

- Every function, method, and class must contain its full production logic. Stub implementations (`pass`, `...`, `raise NotImplementedError`, `# TODO`, placeholder returns) are never acceptable.
- If a task depends on code that does not exist yet, implement the dependency or raise it as a blocker -- do not stub it out.
- All code paths must be exercised by tests. If tests pass against a stub, the tests are wrong.
- Keep changes focused and minimal. Work on ONE task per iteration.

## Progress Report

APPEND to PROGRESS.md (never replace existing content):

```
## [Date/Time] - [Task Description]
- What was implemented
- Files changed
- **Learnings for future iterations:**
  - Patterns discovered (e.g., "this codebase uses X for Y")
  - Gotchas encountered (e.g., "don't forget to update Z when changing W")
  - Useful context (e.g., "the config model is in src/wiggum/config.py")
---
```

The learnings section is critical -- it helps future iterations avoid repeating mistakes.

## Consolidate Patterns

If you discover a reusable pattern that future iterations should know, add it to the `## Codebase Patterns` section at the TOP of PROGRESS.md (create it if it does not exist):

```
## Codebase Patterns
- Use keyword-only arguments after * for functions with 3+ parameters
- Tests mirror src/ structure: src/wiggum/foo.py -> tests/test_foo.py
- All CLI commands go through cyclopts sub-apps
```

Only add patterns that are general and reusable, not task-specific details.

## Updating CLAUDE.md Files

Before committing, check if edited files have learnings worth preserving in nearby CLAUDE.md files:

Worth adding:
- API patterns or conventions specific to that module
- Gotchas or non-obvious requirements
- Dependencies between files
- Testing approaches for that area

Not worth adding:
- Task-specific implementation details
- Temporary debugging notes
- Information already in PROGRESS.md
