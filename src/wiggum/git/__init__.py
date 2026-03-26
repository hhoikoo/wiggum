"""Git integration package."""

from collections.abc import (
    Sequence,  # noqa: TC003 -- needed at runtime for @runtime_checkable
)
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from wiggum.git.models import LogEntry, StatusEntry

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class GitClient(Protocol):
    """Structural interface for git operations."""

    def repo_root(self) -> Path:
        """Return the root directory of the git repository."""
        ...

    def is_repo(self) -> bool:
        """Return whether the path is inside a git repository."""
        ...

    def current_branch(self) -> str:
        """Return the name of the current branch."""
        ...

    def status(self) -> Sequence[StatusEntry]:
        """Return the list of status entries for the working tree."""
        ...

    def diff(self, *, staged: bool = False) -> str:
        """Return the diff output, optionally for staged changes only."""
        ...

    def diff_names(self, *, staged: bool = False) -> Sequence[str]:
        """Return file names with differences."""
        ...

    def log(self, *, max_count: int = 10) -> Sequence[LogEntry]:
        """Return recent log entries up to max_count."""
        ...

    def add(self, paths: Sequence[str]) -> None:
        """Stage the given file paths."""
        ...

    def stage_all(self) -> None:
        """Stage all changes in the working tree."""
        ...

    def commit(self, message: str) -> None:
        """Create a commit with the given message."""
        ...

    def fetch(self, remote: str, branch: str) -> None:
        """Fetch a branch from a remote."""
        ...

    def rebase(self, onto: str) -> bool:
        """Rebase onto the given ref, returning True on success, False on conflict."""
        ...

    def rebase_continue(self) -> bool:
        """Continue an in-progress rebase, returning True on success, False on conflict."""
        ...

    def rebase_abort(self) -> None:
        """Abort an in-progress rebase."""
        ...

    def default_branch(self) -> str:
        """Return the default branch name from origin/HEAD, falling back to main."""
        ...


GitPort = GitClient

__all__ = ["GitClient", "GitPort", "LogEntry", "StatusEntry"]
