## Ralph Loop Principles

1. This invocation does exactly ONE thing. Not one feature -- one thing.
2. Never expand scope. If you find a gap or issue, output a line starting with NEW_TODO: and move on. Do not attempt to address it.
3. Fresh context. You have no memory of prior invocations.
4. Minimal changes. Write the minimum code for the task at hand.
5. Follow project conventions: Python 3.14+, src layout (src/wiggum/), pyright strict, pytest, uv.
6. Use `uv run` for all tool invocations (ruff, pytest, pyright).
7. All public classes, methods, and functions must have a one-line docstring.
8. Imports used only in type annotations must be inside `if TYPE_CHECKING:` blocks. Exception: runtime_checkable Protocols need their annotation types at runtime -- use `# noqa: TC003` for those.
9. Use modern Python syntax: PEP 695 type parameters, not TypeVar.
10. ASCII only in code and comments.
