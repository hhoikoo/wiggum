"""Implementation directory utilities: validation, skeleton creation, path resolution."""

import sys
from pathlib import Path

_WIGGUM_DIR = ".wiggum"
_IMPL_DIR = "implementation"

_PLAN_FILENAME = "IMPLEMENTATION_PLAN.md"
_PROGRESS_FILENAME = "PROGRESS.md"

_PLAN_SKELETON = """\
# Implementation Plan

## Tasks

"""

_PROGRESS_SKELETON = """\
# Progress

"""


def _find_git_root(*, start: Path | None = None) -> Path | None:
    """Walk upward from *start* (default: cwd) to find the git root."""
    current = (start or Path.cwd()).resolve()
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def impl_dir_path(ticket: str, *, root: Path | None = None) -> Path:
    """Return the implementation directory path for a ticket relative to git root."""
    git_root = root or _find_git_root()
    if git_root is None:
        print("fatal: not a git repository", file=sys.stderr)  # noqa: T201
        sys.exit(2)
    return git_root / _WIGGUM_DIR / _IMPL_DIR / ticket


def validate_impl_dir(ticket: str, *, root: Path | None = None) -> Path:
    """Validate that the implementation directory exists, exiting with code 2 if not."""
    path = impl_dir_path(ticket, root=root)
    if not path.is_dir():
        print(  # noqa: T201
            f"fatal: implementation directory does not exist: {path}",
            file=sys.stderr,
        )
        sys.exit(2)
    return path


def create_skeleton_files(impl_path: Path) -> None:
    """Create skeleton IMPLEMENTATION_PLAN.md and PROGRESS.md if they do not exist."""
    plan = impl_path / _PLAN_FILENAME
    if not plan.exists():
        plan.write_text(_PLAN_SKELETON)

    progress = impl_path / _PROGRESS_FILENAME
    if not progress.exists():
        progress.write_text(_PROGRESS_SKELETON)


def resolve_plan_path(impl_path: Path) -> Path:
    """Return the IMPLEMENTATION_PLAN.md path within an implementation directory."""
    return impl_path / _PLAN_FILENAME


def resolve_progress_path(impl_path: Path) -> Path:
    """Return the PROGRESS.md path within an implementation directory."""
    return impl_path / _PROGRESS_FILENAME
