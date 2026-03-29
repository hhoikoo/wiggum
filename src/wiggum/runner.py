"""Runner loops for plan and build phases."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from wiggum.impl_dir import (
    create_skeleton_files,
    find_git_root,
    impl_dir_path,
    resolve_plan_path,
    resolve_progress_path,
    validate_impl_dir,
)
from wiggum.json_extract import extract_last_fenced_json
from wiggum.plan import parse_plan
from wiggum.progress import Outcome, append_iteration
from wiggum.prompts import render_build_prompt, render_plan_prompt
from wiggum.subprocess_util import invoke_claude

if TYPE_CHECKING:
    from pathlib import Path

    from wiggum.config import Config

_SPECS_DIR = ".wiggum/specs"
_STATUS_COMPLETE = "complete"


def resolve_specs(issue_id: str, *, root: Path | None = None) -> str:
    """Read all files in .wiggum/specs/<issue-id>/ and return concatenated content.

    Exits with code 2 if the specs directory does not exist.
    """
    git_root = root or find_git_root()
    if git_root is None:
        print("fatal: not a git repository", file=sys.stderr)  # noqa: T201
        sys.exit(2)
    specs_path = git_root / _SPECS_DIR / issue_id
    if not specs_path.is_dir():
        print(  # noqa: T201
            f"fatal: specs directory does not exist: {specs_path}",
            file=sys.stderr,
        )
        sys.exit(2)

    parts = [f.read_text() for f in sorted(specs_path.iterdir()) if f.is_file()]
    return "\n".join(parts)


def run_plan(
    issue_id: str,
    *,
    config: Config,
    root: Path | None = None,
) -> int:
    """Run the plan-mode loop up to max_plan_iterations.

    Returns 0 on completion, 1 if max iterations reached without completion.
    Exits with code 2 on startup failures (missing specs directory).
    """
    specs_content = resolve_specs(issue_id, root=root)
    impl_path = impl_dir_path(issue_id, root=root)
    impl_path.mkdir(parents=True, exist_ok=True)
    create_skeleton_files(impl_path)

    max_iters = config.loop.max_plan_iterations
    plan_model = config.model.plan
    model = plan_model if plan_model.name else None

    for i in range(1, max_iters + 1):
        print(f"[plan] iteration {i}/{max_iters}", file=sys.stderr)  # noqa: T201
        prompt = render_plan_prompt(
            issue_id=issue_id,
            specs_content=specs_content,
            impl_path=impl_path,
        )
        result = invoke_claude(prompt, model=model)

        status_block = extract_last_fenced_json(result.stdout)
        status = status_block.get("status") if status_block else None

        if status == _STATUS_COMPLETE:
            print("[plan] complete", file=sys.stderr)  # noqa: T201
            return 0

    print(  # noqa: T201
        f"[plan] max iterations ({max_iters}) reached without completion",
        file=sys.stderr,
    )
    return 1


def run_build(
    issue_id: str,
    *,
    config: Config,
    root: Path | None = None,
) -> int:
    """Run the build-mode loop up to max_build_iterations.

    Returns 0 when all tasks complete, 1 if max iterations reached.
    Exits with code 2 on startup failures (missing impl dir or plan file).
    Prints a JSON summary to stdout at loop exit.
    """
    impl_path = validate_impl_dir(issue_id, root=root)
    plan_path = resolve_plan_path(impl_path)
    progress_path = resolve_progress_path(impl_path)

    if not plan_path.exists():
        print(  # noqa: T201
            f"fatal: IMPLEMENTATION_PLAN.md does not exist: {plan_path}",
            file=sys.stderr,
        )
        sys.exit(2)

    max_iters = config.loop.max_build_iterations
    build_model = config.model.build
    model = build_model if build_model.name else None
    quality_commands = config.loop.quality_commands
    completed = 0

    for i in range(1, max_iters + 1):
        state = parse_plan(plan_path)
        task = state.top_unchecked()

        if task is None:
            break

        print(  # noqa: T201
            f"[build] iteration {i}/{max_iters}: {task.description}",
            file=sys.stderr,
        )
        prompt = render_build_prompt(
            issue_id=issue_id,
            task_description=task.description,
            impl_path=impl_path,
            quality_commands=quality_commands,
        )
        result = invoke_claude(prompt, model=model)

        state.mark_complete(task.line_number)
        state.write()
        completed += 1

        outcome = Outcome.PASS if result.exit_code == 0 else Outcome.FAIL
        append_iteration(
            path=progress_path,
            task=task.description,
            outcome=outcome,
        )

    state = parse_plan(plan_path)
    all_done = state.all_complete()
    exit_code = 0 if all_done else 1

    summary = {
        "issue_id": issue_id,
        "completed_tasks": completed,
        "total_tasks": len(state.tasks),
        "all_complete": all_done,
        "exit_code": exit_code,
    }
    print(json.dumps(summary))  # noqa: T201

    if not all_done:
        print(  # noqa: T201
            f"[build] max iterations ({max_iters}) reached without completion",
            file=sys.stderr,
        )

    return exit_code


def run_combined(
    issue_id: str,
    *,
    config: Config,
    root: Path | None = None,
) -> int:
    """Run plan mode followed by build mode without user confirmation.

    Returns 0 when all tasks complete, 1 if max iterations reached.
    Exits with code 2 on startup failures, 130 on SIGINT.
    """
    run_plan(issue_id, config=config, root=root)
    return run_build(issue_id, config=config, root=root)
