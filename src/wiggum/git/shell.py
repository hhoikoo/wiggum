"""Subprocess-based git adapter."""

import subprocess
from collections.abc import (
    Sequence,  # noqa: TC003 - needed at runtime for inspect.signature
)
from pathlib import Path

from wiggum.git.models import LogEntry, StatusEntry

_RECORD_SEP = "---RECORD---"


class SubprocessGit:
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

    def repo_root(self) -> Path:
        """Return the root directory of the git repository."""
        return Path(self._run("rev-parse", "--show-toplevel"))

    def is_repo(self) -> bool:
        """Return whether the path is inside a git repository."""
        try:
            self._run("rev-parse", "--git-dir")
        except subprocess.CalledProcessError:
            return False
        return True

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

    def diff_names(self, *, staged: bool = False) -> list[str]:
        """Return file names with differences."""
        args = ["diff", "--name-only"]
        if staged:
            args.append("--staged")
        raw = self._run(*args)
        if not raw:
            return []
        return raw.splitlines()

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

    def add(self, paths: Sequence[str]) -> None:
        """Stage files for commit."""
        self._run("add", *paths)

    def stage_all(self) -> None:
        """Stage all changes in the working tree."""
        self._run("add", ".")

    def commit(self, message: str) -> None:
        """Create a commit with the given message."""
        self._run("commit", "-m", message)

    def fetch(self, remote: str, branch: str) -> None:
        """Fetch a branch from a remote."""
        self._run("fetch", remote, branch)

    def rebase(self, onto: str) -> bool:
        """Rebase the current branch onto the given ref."""
        try:
            self._run("rebase", onto)
        except subprocess.CalledProcessError:
            return False
        return True

    def rebase_abort(self) -> None:
        """Abort an in-progress rebase."""
        self._run("rebase", "--abort")

    def default_branch(self) -> str:
        """Return the default branch name from origin/HEAD or fall back to main."""
        try:
            ref = self._run("symbolic-ref", "refs/remotes/origin/HEAD")
            return ref.removeprefix("refs/remotes/origin/")
        except subprocess.CalledProcessError:
            return "main"


ShellGitAdapter = SubprocessGit
