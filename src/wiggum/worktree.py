"""Worktree symlink management."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_log = logging.getLogger(__name__)


def ensure_symlinks(
    repo_root: Path,
    worktree_path: Path,
    directories: Sequence[str],
) -> None:
    """Create symlinks from worktree into repo root for each directory."""
    for name in directories:
        source = repo_root / name
        target = worktree_path / name

        if not source.exists():
            _log.info("skipping %s: source does not exist in repo root", name)
            continue

        if target.exists() or target.is_symlink():
            _log.info("skipping %s: target already exists in worktree", name)
            continue

        target.symlink_to(source)
        _log.info("created symlink %s -> %s", target, source)
