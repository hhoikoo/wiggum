"""Tests for ShellGitAdapter -- subprocess-based GitPort implementation."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with one commit."""
    run = lambda *args: subprocess.run(  # noqa: E731
        args, cwd=tmp_path, capture_output=True, check=True
    )
    run("git", "init")
    run("git", "config", "user.email", "test@test.com")
    run("git", "config", "user.name", "Test")
    (tmp_path / "initial.txt").write_text("hello")
    run("git", "add", ".")
    run("git", "commit", "-m", "initial commit")
    return tmp_path


class TestCurrentBranch:
    def test_returns_default_branch_name(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        branch = adapter.current_branch()
        # git init creates either "main" or "master" depending on config
        assert branch in {"main", "master"}

    def test_returns_feature_branch_after_checkout(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        subprocess.run(
            ["git", "checkout", "-b", "feat/test"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        adapter = ShellGitAdapter(repo_path=git_repo)
        assert adapter.current_branch() == "feat/test"


class TestStatus:
    def test_empty_status_on_clean_repo(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        entries = adapter.status()
        assert entries == []

    def test_status_includes_new_file(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "new.txt").write_text("new file")
        adapter = ShellGitAdapter(repo_path=git_repo)
        entries = adapter.status()
        assert len(entries) > 0
        paths = [e.path for e in entries]
        assert "new.txt" in paths

    def test_status_includes_modified_file(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "initial.txt").write_text("modified")
        adapter = ShellGitAdapter(repo_path=git_repo)
        entries = adapter.status()
        paths = [e.path for e in entries]
        assert "initial.txt" in paths


class TestDiff:
    def test_diff_empty_on_clean_repo(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        result = adapter.diff()
        assert result == ""

    def test_diff_shows_modification(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "initial.txt").write_text("changed content")
        adapter = ShellGitAdapter(repo_path=git_repo)
        result = adapter.diff()
        assert "changed content" in result


class TestLog:
    def test_log_returns_initial_commit(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        entries = adapter.log()
        assert len(entries) >= 1
        assert entries[0].message == "initial commit"
        assert len(entries[0].hash) >= 7

    def test_log_respects_max_count(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        # add a second commit
        (git_repo / "second.txt").write_text("second")
        subprocess.run(
            ["git", "add", "."], cwd=git_repo, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "second commit"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )
        adapter = ShellGitAdapter(repo_path=git_repo)
        entries = adapter.log(max_count=1)
        assert len(entries) == 1
        assert entries[0].message == "second commit"


class TestAdd:
    def test_add_stages_file(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "staged.txt").write_text("stage me")
        adapter = ShellGitAdapter(repo_path=git_repo)
        adapter.add("staged.txt")
        # verify file is staged via git status --porcelain
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "A  staged.txt" in result.stdout

    def test_add_stages_multiple_files(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "a.txt").write_text("a")
        (git_repo / "b.txt").write_text("b")
        adapter = ShellGitAdapter(repo_path=git_repo)
        adapter.add("a.txt", "b.txt")
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "A  a.txt" in result.stdout
        assert "A  b.txt" in result.stdout


class TestRepoRoot:
    def test_returns_path_object(self, git_repo: Path) -> None:
        from pathlib import Path as PathCls

        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        root = adapter.repo_root()
        assert isinstance(root, PathCls)

    def test_returns_repo_root_directory(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        root = adapter.repo_root()
        assert root == git_repo

    def test_resolves_from_subdirectory(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        subdir = git_repo / "subdir"
        subdir.mkdir()
        adapter = ShellGitAdapter(repo_path=subdir)
        root = adapter.repo_root()
        assert root == git_repo


class TestIsRepo:
    def test_true_for_git_repo(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        assert adapter.is_repo() is True

    def test_false_for_non_repo(self, tmp_path: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=tmp_path)
        assert adapter.is_repo() is False


class TestStageAll:
    def test_stages_all_new_files(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "a.txt").write_text("a")
        (git_repo / "b.txt").write_text("b")
        adapter = ShellGitAdapter(repo_path=git_repo)
        adapter.stage_all()
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "A  a.txt" in result.stdout
        assert "A  b.txt" in result.stdout

    def test_stages_modified_files(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "initial.txt").write_text("modified")
        adapter = ShellGitAdapter(repo_path=git_repo)
        adapter.stage_all()
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "M  initial.txt" in result.stdout


class TestDiffNames:
    def test_empty_on_clean_repo(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        names = adapter.diff_names()
        assert names == []

    def test_returns_modified_file_names(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "initial.txt").write_text("changed")
        adapter = ShellGitAdapter(repo_path=git_repo)
        names = adapter.diff_names()
        assert "initial.txt" in names

    def test_returns_staged_file_names(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "initial.txt").write_text("staged change")
        subprocess.run(
            ["git", "add", "."], cwd=git_repo, capture_output=True, check=True
        )
        adapter = ShellGitAdapter(repo_path=git_repo)
        names = adapter.diff_names(staged=True)
        assert "initial.txt" in names

    def test_returns_sequence_of_strings(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "new.txt").write_text("new")
        adapter = ShellGitAdapter(repo_path=git_repo)
        names = adapter.diff_names()
        assert all(isinstance(n, str) for n in names)


class TestCommit:
    def test_commit_creates_new_commit(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "committed.txt").write_text("commit me")
        subprocess.run(
            ["git", "add", "."], cwd=git_repo, capture_output=True, check=True
        )
        adapter = ShellGitAdapter(repo_path=git_repo)
        adapter.commit("test commit message")
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "test commit message" in result.stdout
