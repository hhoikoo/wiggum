"""CLI entry point for wiggum."""

import sys
from pathlib import Path  # noqa: TC003 - cyclopts needs Path at runtime for arg parsing

import cyclopts

from wiggum.agent.shell import SubprocessAgent
from wiggum.config import load_config, validate_startup
from wiggum.git.shell import SubprocessGit
from wiggum.outer_loop import outer_loop
from wiggum.plan import reset_all_checked

app = cyclopts.App(name="wiggum")


@app.command
def run(plan: Path) -> None:
    """Run the ralph loop on a plan file."""
    if not plan.is_file():
        msg = f"Plan file not found: {plan}"
        raise FileNotFoundError(msg)

    git = SubprocessGit(repo_path=plan.parent)
    repo_root = git.repo_root()

    validate_startup(repo_path=repo_root)
    config = load_config(repo_root)
    agent = SubprocessAgent(work_dir=repo_root)

    try:
        outer_loop(plan_path=plan, agent=agent, git=git, config=config)
    except KeyboardInterrupt:
        plan.write_text(reset_all_checked(plan.read_text()))
        sys.exit(130)
