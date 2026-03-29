# Research: cyclopts nested subcommands and app composition

## Research question

How does the cyclopts Python library handle nested subcommands and app composition? Specifically, how to add a `run` command group with sub-subcommands `plan` and `build` to an existing cyclopts `App`.

## Project overview

cyclopts is a Python CLI framework (requires Python >=3.10) that builds CLIs from type hints. The primary source of truth for this research is the official docs at `https://cyclopts.readthedocs.io` and the GitHub source at `https://github.com/BrianPugh/cyclopts`. The current wiggum CLI entry point is `src/wiggum/cli.py`, which creates a bare `cyclopts.App(name="wiggum")`.

## Findings

### Pattern 1: Sub-app registration via `app.command(App(...))`

**Location:** `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/commands.rst`

**Description:** To create a nested command group, instantiate a child `App` with a `name` and register it as a command on the parent via `app.command(sub_app)`. Functions registered on the sub-app then become sub-subcommands:

```python
from cyclopts import App

app = App(name="wiggum")
run_app = App(name="run")
app.command(run_app)

@run_app.command
def plan(...):
    ...

@run_app.command
def build(...):
    ...
```

This yields `wiggum run plan ...` and `wiggum run build ...`.

The one-liner form is also valid:

```python
run_app = app.command(App(name="run"))
```

**Relevance:** This is the direct pattern needed to add `run plan` and `run build` under the existing `wiggum` app.

### Pattern 2: Dictionary-style access to sub-apps

**Location:** `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/commands.rst`

**Description:** After a sub-app is registered, its commands can also be defined by accessing the parent with bracket notation:

```python
@app["run"].command
def plan(...):
    ...
```

**Relevance:** Useful when sub-app registration and command definition happen in separate files. The sub-app must be registered with `app.command(...)` before this notation works.

### Pattern 3: Default action on a sub-app

**Location:** `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/commands.rst`

**Description:** A sub-app can have its own default action -- the function run when the user types `wiggum run` without a sub-subcommand. Register it with `@run_app.default`:

```python
@run_app.default
def run_default():
    # runs when user invokes "wiggum run" with no further args
    ...
```

Without a default, cyclopts displays the sub-app's help page when no sub-subcommand is given.

**Relevance:** Determines what happens when a user types `wiggum run` alone. Displaying help is the safe default (no `@run_app.default` needed for that behavior).

### Pattern 4: Configuration inheritance and override

**Location:** `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/commands.rst`

**Description:** Child apps inherit settings from their parent (`exit_on_error`, `print_error`, etc.). A child can override selectively:

```python
root_app = App(name="wiggum", exit_on_error=True)
run_app = root_app.command(App(name="run"))             # inherits exit_on_error=True
build_app = run_app.command(App(name="build", exit_on_error=False))  # override
```

**Relevance:** wiggum can centralize error handling on the root app; `run`, `plan`, `build` inherit it unless explicitly overridden.

### Pattern 5: Command naming -- underscores become hyphens

**Location:** `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/commands.rst`

**Description:** By default, Python function names have underscores replaced with hyphens for CLI command names. Leading/trailing underscores are stripped. To rename explicitly, use `@app.command(name="custom-name")`. The `name_transform` attribute on `App` can change this globally.

**Relevance:** A function `def plan_and_build()` becomes the CLI command `plan-and-build`. For simple names like `plan` and `build` this is transparent.

### Pattern 6: Help text for sub-apps

**Location:** `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/commands.rst`

**Description:** Help text for a sub-app command group comes from the `help` parameter of the `App` constructor, not from a function docstring (since there is no function). For leaf commands, the function docstring short description is used.

```python
run_app = App(name="run", help="Execute the feature pipeline.")
app.command(run_app)

@run_app.command
def plan():
    """Plan the feature implementation."""
    ...
```

**Relevance:** Sets the one-line description shown in `wiggum --help` for the `run` group.

### Pattern 7: Parameter type annotations

**Location:** `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/parameters.rst`

**Description:** cyclopts derives CLI argument names, types, and help text directly from function signatures and docstrings. Use `Annotated[T, Parameter(...)]` for fine-grained control:

```python
from typing import Annotated
from cyclopts import Parameter

@run_app.command
def plan(ticket: Annotated[str, Parameter(help="GitHub issue number")]) -> None:
    ...
```

`Optional` types become optional CLI flags. Boolean flags default to `--flag / --no-flag` patterns.

**Relevance:** Guides how to define the parameter signatures for `plan` and `build` commands.

### Pattern 8: Flattening sub-apps (not recommended here)

**Location:** `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/commands.rst`

**Description:** Registering a sub-app with `name="*"` flattens all its commands directly into the parent, removing the intermediate name. Caveats: no additional configuration kwargs allowed, only `App` instances can be flattened.

**Relevance:** Not applicable for the `run plan` / `run build` use case, which intentionally wants the `run` namespace. Documented here to avoid accidentally using it.

## Recommendations

**Adopt directly:**

Use the two-level pattern: create `run_app = app.command(App(name="run", help="..."))`, then register `plan` and `build` as `@run_app.command` functions. This is idiomatic cyclopts and requires no library extensions.

Keep all CLI definitions in `src/wiggum/cli.py` or split into a `src/wiggum/commands/run.py` module that is imported in `cli.py`. Either approach works; the sub-app can be defined in a separate module and registered at import time.

Do not add `@run_app.default` unless a meaningful action for bare `wiggum run` is needed -- omitting it causes cyclopts to show the `run` group's help page, which is the correct default behavior.

**Adapt:**

Use `App(name="run", help="...")` to provide the one-line description visible in `wiggum --help`. Use function docstrings for `plan` and `build` to provide their per-command descriptions.

**Avoid:**

- `name="*"` flattening -- it removes the `run` namespace.
- Registering sub-apps with `@app.default` -- the docs explicitly state this is not allowed.
- Manually calling `app()` in sub-app modules -- only the root `app()` call in the entry point should trigger execution.

## Minimal example for wiggum

```python
import cyclopts

app = cyclopts.App(name="wiggum")
run_app = app.command(cyclopts.App(name="run", help="Execute the feature pipeline."))

@run_app.command
def plan() -> None:
    """Plan the feature implementation."""
    ...

@run_app.command
def build() -> None:
    """Build the feature."""
    ...
```

Invocations: `wiggum run plan`, `wiggum run build`, `wiggum run --help`.

## References

- `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/commands.rst` -- primary source for sub-app registration, default actions, naming, help text, and configuration inheritance
- `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/parameters.rst` -- parameter types, `Annotated`, `Parameter` class
- `https://raw.githubusercontent.com/BrianPugh/cyclopts/main/docs/source/api.rst` -- full `App` constructor signature and method list
- `/Users/hhkoo/Developer/wiggum/.wiggum/worktrees/10/src/wiggum/cli.py` -- current wiggum CLI entry point (bare `App` with no commands)
