"""Wiggum CLI -- root app and ``run`` sub-app with plan/build commands."""

import sys
from typing import Annotated

import cyclopts

from wiggum.config import Config, load_config
from wiggum.runner import run_build, run_combined, run_plan

app = cyclopts.App(name="wiggum")
run_app = cyclopts.App(name="run", help="Run the plan/build loop for an issue.")
app.command(run_app)


def _apply_overrides(
    cfg: Config,
    *,
    max_iterations: int | None,
    model: str | None,
    mode: str,
) -> Config:
    """Return a new Config with CLI overrides applied."""
    loop_overrides: dict[str, object] = {}
    if max_iterations is not None:
        if mode == "plan":
            loop_overrides["max_plan_iterations"] = max_iterations
        else:
            loop_overrides["max_build_iterations"] = max_iterations

    model_phase = cfg.model
    if model is not None:
        name_override = {"name": model}
        if mode == "plan":
            model_phase = model_phase.model_copy(
                update={"plan": model_phase.plan.model_copy(update=name_override)}
            )
        elif mode == "build":
            model_phase = model_phase.model_copy(
                update={"build": model_phase.build.model_copy(update=name_override)}
            )
        else:
            model_phase = model_phase.model_copy(
                update={
                    "plan": model_phase.plan.model_copy(update=name_override),
                    "build": model_phase.build.model_copy(update=name_override),
                }
            )

    return cfg.model_copy(
        update={
            "loop": cfg.loop.model_copy(update=loop_overrides),
            "model": model_phase,
        },
    )


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
    cfg = _apply_overrides(
        load_config(), max_iterations=max_iterations, model=model, mode="plan"
    )
    sys.exit(run_plan(issue_id, config=cfg))


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
    cfg = _apply_overrides(
        load_config(), max_iterations=max_iterations, model=model, mode="build"
    )
    sys.exit(run_build(issue_id, config=cfg))


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
    cfg = _apply_overrides(
        load_config(), max_iterations=max_iterations, model=model, mode="combined"
    )
    sys.exit(run_combined(issue_id, config=cfg))
