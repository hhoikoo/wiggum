"""Git port protocol defining the interface for git operations."""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wiggum.git.models import LogEntry, StatusEntry


@runtime_checkable
class GitPort(Protocol):
    """Structural interface for git operations."""

    def current_branch(self) -> str:
        """Return the name of the current branch."""
        ...

    def status(self) -> Sequence[StatusEntry]:
        """Return the list of status entries for the working tree."""
        ...

    def diff(self, *, staged: bool = False) -> str:
        """Return the diff output, optionally for staged changes only."""
        ...

    def log(self, *, max_count: int = 10) -> Sequence[LogEntry]:
        """Return recent log entries up to max_count."""
        ...

    def add(self, paths: Sequence[str]) -> None:
        """Stage the given file paths."""
        ...

    def commit(self, message: str) -> None:
        """Create a commit with the given message."""
        ...
