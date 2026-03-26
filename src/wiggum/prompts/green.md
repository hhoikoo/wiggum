## Task: Implement Fix (GREEN)

Working directory: {working_dir}

### What to fix

{tasks}

### Existing plan (do NOT output NEW_TODO for anything already listed here)

{plan_text}

### Instructions

1. Read relevant tests and source code to understand what is expected.
2. Write the MINIMUM code to make it work.
3. Run `uv run ruff check --fix --unsafe-fixes` on files you changed and fix any remaining lint errors.
4. Do NOT run pytest -- the harness handles that.
5. Do NOT write new tests.
6. Do NOT refactor unrelated code.
7. Only output NEW_TODO: for gaps that are NOT already in the plan above.
