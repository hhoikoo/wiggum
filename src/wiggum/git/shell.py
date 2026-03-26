"""Subprocess-based git adapter."""

import subprocess
from typing import TYPE_CHECKING

from wiggum.git.models import LogEntry, StatusEntry

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_RECORD_SEP = "---RECORD---"


class ShellGitAdapter:
    """Git operations via subprocess calls."""

    def __init__(self, *, repo_path: Path) -> None:
        """Initialize with the path to a git repository."""
        self._repo_path = repo_path

    def _run(self, *args: str) -> str:
        result = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=self._repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.rstrip()

    def current_branch(self) -> str:
        """Return the name of the current branch."""
        return self._run("rev-parse", "--abbrev-ref", "HEAD")

    def status(self) -> Sequence[StatusEntry]:
        """Return status entries for changed files."""
        raw = self._run("status", "--porcelain")
        if not raw:
            return []
        entries: list[StatusEntry] = []
        for line in raw.splitlines():
            path = line[3:]
            entries.append(StatusEntry(path=path))
        return entries

    def diff(self, *, staged: bool = False) -> str:
        """Return the diff output."""
        args = ["diff"]
        if staged:
            args.append("--staged")
        return self._run(*args)

    def log(self, *, max_count: int = 10) -> Sequence[LogEntry]:
        """Return recent log entries."""
        raw = self._run(
            "log",
            f"--max-count={max_count}",
            f"--format=%H{_RECORD_SEP}%s",
        )
        if not raw:
            return []
        entries: list[LogEntry] = []
        for line in raw.splitlines():
            hash_, message = line.split(_RECORD_SEP, maxsplit=1)
            entries.append(LogEntry(message=message, hash=hash_))
        return entries

    def add(self, *paths: str) -> None:
        """Stage files for commit."""
        self._run("add", *paths)

    def commit(self, message: str) -> None:
        """Create a commit with the given message."""
        self._run("commit", "-m", message)
