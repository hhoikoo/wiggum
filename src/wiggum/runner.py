"""Runner loops for plan and build phases."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from wiggum.impl_dir import (
    create_skeleton_files,
    find_git_root,
    validate_impl_dir,
)
from wiggum.json_extract import extract_last_fenced_json
from wiggum.prompts import render_plan_prompt
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
    Exits with code 2 on startup failures (missing specs or impl directory).
    """
    specs_content = resolve_specs(issue_id, root=root)
    impl_path = validate_impl_dir(issue_id, root=root)
    create_skeleton_files(impl_path)

    max_iters = config.loop.max_plan_iterations
    model = config.model if config.model.name else None

    for i in range(1, max_iters + 1):
        print(f"[plan] iteration {i}/{max_iters}", file=sys.stderr)  # noqa: T201
        prompt = render_plan_prompt(issue_id=issue_id, specs_content=specs_content)
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
