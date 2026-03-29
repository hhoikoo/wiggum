"""Wiggum CLI -- root app and ``run`` sub-app with plan/build commands."""

from typing import Annotated

import cyclopts

from wiggum.config import load_config

app = cyclopts.App(name="wiggum")
run_app = cyclopts.App(name="run", help="Run the plan/build loop for an issue.")
app.command(run_app)


def _resolve_config(
    *,
    max_iterations: int | None,
    model: str | None,
    mode: str,
) -> dict[str, object]:
    """Load config and apply CLI overrides, returning a dict of resolved values."""
    cfg = load_config()

    if mode == "plan":
        iterations = max_iterations or cfg.loop.max_plan_iterations
    else:
        iterations = max_iterations or cfg.loop.max_build_iterations

    resolved_model = model or cfg.model.name

    return {
        "issue_id": "",
        "max_iterations": iterations,
        "model": resolved_model,
        "mode": mode,
    }


@run_app.command
def plan(
    issue_id: str,
    *,
    max_iterations: Annotated[
        int | None,
        cyclopts.Parameter(
            name="--max-iterations", help="Override max plan iterations."
        ),
    ] = None,
    model: Annotated[
        str | None,
        cyclopts.Parameter(name="--model", help="Override claude model name."),
    ] = None,
) -> None:
    """Run the planning loop for an issue."""
    resolved = _resolve_config(max_iterations=max_iterations, model=model, mode="plan")
    resolved["issue_id"] = issue_id
    print(resolved)  # noqa: T201


@run_app.command
def build(
    issue_id: str,
    *,
    max_iterations: Annotated[
        int | None,
        cyclopts.Parameter(
            name="--max-iterations", help="Override max build iterations."
        ),
    ] = None,
    model: Annotated[
        str | None,
        cyclopts.Parameter(name="--model", help="Override claude model name."),
    ] = None,
) -> None:
    """Run the build loop for an issue."""
    resolved = _resolve_config(max_iterations=max_iterations, model=model, mode="build")
    resolved["issue_id"] = issue_id
    print(resolved)  # noqa: T201


@run_app.default
def run(
    issue_id: str,
    *,
    max_iterations: Annotated[
        int | None,
        cyclopts.Parameter(name="--max-iterations", help="Override max iterations."),
    ] = None,
    model: Annotated[
        str | None,
        cyclopts.Parameter(name="--model", help="Override claude model name."),
    ] = None,
) -> None:
    """Run both plan and build loops for an issue."""
    resolved = _resolve_config(
        max_iterations=max_iterations, model=model, mode="combined"
    )
    resolved["issue_id"] = issue_id
    print(resolved)  # noqa: T201
