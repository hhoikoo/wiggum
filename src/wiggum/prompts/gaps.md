## Task: Find Missing Plan Items

Working directory: {working_dir}

### Current plan (unchecked items only)

{unchecked_items}

### Recently changed source files

{recent_files}

### Instructions

Check the recently changed files above. Identify ONLY items that are required to make the existing plan items work but are missing from the plan. For example: a missing __init__.py that blocks imports, a missing dependency in pyproject.toml, or a function that existing plan items depend on but nobody creates.

Do NOT add:
- Edge cases, error handling, or hardening
- Nice-to-haves or improvements to existing code
- Items that duplicate or overlap with existing plan items
- Items that the inner loop agents can discover on their own via NEW_TODO

Do NOT do a full codebase scan. Focus only on the recently changed files.

Output at most 3 items. Output each as: - [ ] <description>
Output NOTHING else -- no commentary, no preamble, no code fences. If nothing is blocking, output the single word NONE.
