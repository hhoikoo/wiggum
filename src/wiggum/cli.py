"""CLI entry point for wiggum."""

from pathlib import Path  # noqa: TC003 - cyclopts needs Path at runtime for arg parsing

import cyclopts

app = cyclopts.App(name="wiggum")


@app.command
def run(plan: Path) -> None:
    """Run the ralph loop on a plan file."""
    if not plan.is_file():
        msg = f"Plan file not found: {plan}"
        raise FileNotFoundError(msg)
