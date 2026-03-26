from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from wiggum.git.port import GitPort


@dataclass
class _FakeStatusEntry:
    path: str


@dataclass
class _FakeLogEntry:
    message: str
    hash: str


class _ConformingAdapter:
    def current_branch(self) -> str:
        return "main"

    def status(self) -> Sequence[_FakeStatusEntry]:
        return []

    def diff(self, *, staged: bool = False) -> str:
        return ""

    def log(self, *, max_count: int = 10) -> Sequence[_FakeLogEntry]:
        return []

    def add(self, paths: Sequence[str]) -> None:
        return

    def commit(self, message: str) -> None:
        return

    def repo_root(self) -> Path:
        return Path("/fake/repo")

    def is_repo(self) -> bool:
        return True

    def stage_all(self) -> None:
        return

    def diff_names(self) -> Sequence[str]:
        return []


class _MissingMethodAdapter:
    def current_branch(self) -> str:
        return "main"


def test_git_port_is_protocol():
    assert hasattr(GitPort, "__protocol_attrs__") or hasattr(GitPort, "_is_protocol")


def test_git_port_is_runtime_checkable():
    assert isinstance(_ConformingAdapter(), GitPort)


def test_missing_methods_not_instance():
    assert not isinstance(_MissingMethodAdapter(), GitPort)


def test_current_branch_defined():
    assert callable(getattr(GitPort, "current_branch", None))


def test_status_defined():
    assert callable(getattr(GitPort, "status", None))


def test_diff_defined():
    assert callable(getattr(GitPort, "diff", None))


def test_log_defined():
    assert callable(getattr(GitPort, "log", None))


def test_add_defined():
    assert callable(getattr(GitPort, "add", None))


def test_commit_defined():
    assert callable(getattr(GitPort, "commit", None))


def test_repo_root_defined():
    assert callable(getattr(GitPort, "repo_root", None))


def test_is_repo_defined():
    assert callable(getattr(GitPort, "is_repo", None))


def test_stage_all_defined():
    assert callable(getattr(GitPort, "stage_all", None))


def test_diff_names_defined():
    assert callable(getattr(GitPort, "diff_names", None))
