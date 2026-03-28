---
paths:
  - "plugins/**/*"
  - "src/**/*"
  - "tests/**/*"
---
# Code Conventions

Language-agnostic principles. Check other rules in `.claude/rules/` for language-specific conventions.

## Constants and Configuration

- No hardcoded values -- use package-level constants or configuration.
- Config values that vary by environment must be configurable (env vars, config files), not compiled in.

## Function Signatures

- Avoid long positional parameter lists. More than 2-3 positional arguments harms readability and invites argument-order bugs.
- For functions that take many related values, group them into a dedicated config or options struct.
- Callers should be able to read a call site and understand what each argument means without checking the signature.

## Code Organization

- Separate iteration logic from per-item processing logic. No giant loops that do multiple things.
- Extract complex conditions into well-named boolean variables or predicate functions.

## Error Handling

- Catch errors at appropriate boundaries.
- Translate external errors into domain-specific errors with context.
- Never swallow errors silently -- at minimum, log them.
- Follow the existing error handling patterns in the codebase before introducing new ones.
- Error messages should include enough context to diagnose the problem without reading the source code.
- Do not return zero values or defaults that hide real problems. If a function cannot produce a meaningful result, return an error.

## DRY

- If the same logic appears three times, extract it. Two occurrences are a judgment call; three is a strict signal to abstract.
- Abstraction targets: utility functions, shared constants, configuration objects, interfaces. Pick the simplest mechanism that removes the duplication.

## Dead Code

- No commented-out code -- delete it; git has history.
