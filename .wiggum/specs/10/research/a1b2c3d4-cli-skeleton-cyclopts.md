# Research: CLI Skeleton and cyclopts Patterns

## Question

How does the current wiggum CLI skeleton work with cyclopts, and what patterns exist for adding subcommands?

## Findings

### Entry Point

- `pyproject.toml` line 17: `wiggum = "wiggum.cli:app"` -- cyclopts `App` used directly as console_scripts entry point
- `src/wiggum/cli.py`: two lines -- `import cyclopts` and `app = cyclopts.App(name="wiggum")`
- No commands, no subcommands, no default handler registered

### cyclopts v4 Patterns (pinned at 4.10.1)

- Flat commands: `@app.command` decorator on functions
- Grouped subcommands (e.g., `wiggum run plan`): create child `cyclopts.App`, register with `app.command(child_app, name="run")`
- Parameters declared via Python type annotations and default values -- no schema DSL
- Async commands supported natively

### Package Structure

- `__init__.py` is empty (no public API re-exported)
- No `commands/` module structure exists -- clean slate
- No CLI tests exist (only empty `conftest.py` in `tests/`)

### Testing Pattern

- cyclopts apps testable via `app(["subcommand", "--flag"], exit_on_error=False)`

## Gaps

- No default command handler (bare `wiggum` only shows help)
- No subcommand module structure
- No async wiring
- No tests
