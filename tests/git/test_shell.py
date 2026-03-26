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
    def test_add_stages_file_with_sequence(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "staged.txt").write_text("stage me")
        adapter = ShellGitAdapter(repo_path=git_repo)
        adapter.add(["staged.txt"])
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "A  staged.txt" in result.stdout

    def test_add_stages_multiple_files_with_sequence(self, git_repo: Path):
        from wiggum.git.shell import ShellGitAdapter

        (git_repo / "a.txt").write_text("a")
        (git_repo / "b.txt").write_text("b")
        adapter = ShellGitAdapter(repo_path=git_repo)
        adapter.add(["a.txt", "b.txt"])
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "A  a.txt" in result.stdout
        assert "A  b.txt" in result.stdout

    def test_add_signature_matches_git_port(self, git_repo: Path):
        from wiggum.git import GitPort
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        port_add = GitPort.add
        adapter_add = adapter.add
        # Protocol requires (self, paths: Sequence[str]) -> None
        # Verify parameter count matches (self + paths = 2 on unbound method)
        import inspect

        _port_params = list(inspect.signature(port_add).parameters)
        adapter_params = list(inspect.signature(adapter_add).parameters)
        # Bound method: port has ['self', 'paths'], adapter bound has ['paths']
        assert "paths" in adapter_params
        sig = inspect.signature(adapter_add)
        param = sig.parameters["paths"]
        assert param.kind != inspect.Parameter.VAR_POSITIONAL


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


def _run_git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.rstrip()


@pytest.fixture
def cloned_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Create an upstream repo and a local clone with origin configured."""
    upstream = tmp_path / "upstream"
    upstream.mkdir()
    _run_git(upstream, "init", "--bare")

    local = tmp_path / "local"
    _run_git(tmp_path, "clone", str(upstream), "local")
    _run_git(local, "config", "user.email", "test@test.com")
    _run_git(local, "config", "user.name", "Test")
    (local / "initial.txt").write_text("hello")
    _run_git(local, "add", ".")
    _run_git(local, "commit", "-m", "initial commit")
    _run_git(local, "push", "-u", "origin", "HEAD")
    return upstream, local


class TestFetch:
    def test_fetch_retrieves_remote_commits(
        self,
        cloned_repo: tuple[Path, Path],
    ) -> None:
        from wiggum.git.shell import ShellGitAdapter

        upstream, local = cloned_repo
        # Create a second clone, push a new commit, then fetch from the first
        second = local.parent / "second"
        _run_git(local.parent, "clone", str(upstream), "second")
        _run_git(second, "config", "user.email", "test@test.com")
        _run_git(second, "config", "user.name", "Test")
        (second / "new.txt").write_text("from second clone")
        _run_git(second, "add", ".")
        _run_git(second, "commit", "-m", "second clone commit")
        branch = _run_git(second, "rev-parse", "--abbrev-ref", "HEAD")
        _run_git(second, "push", "origin", branch)

        adapter = ShellGitAdapter(repo_path=local)
        adapter.fetch("origin", branch)

        # The remote-tracking ref should now include the new commit
        log = _run_git(local, "log", "--oneline", f"origin/{branch}")
        assert "second clone commit" in log

    def test_fetch_raises_on_invalid_remote(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        adapter = ShellGitAdapter(repo_path=git_repo)
        with pytest.raises(subprocess.CalledProcessError):
            adapter.fetch("nonexistent", "main")


class TestRebase:
    def test_rebase_returns_true_on_success(
        self,
        cloned_repo: tuple[Path, Path],
    ) -> None:
        from wiggum.git.shell import ShellGitAdapter

        _upstream, local = cloned_repo
        branch = _run_git(local, "rev-parse", "--abbrev-ref", "HEAD")
        # Create a feature branch with one commit
        _run_git(local, "checkout", "-b", "feat/rebase-test")
        (local / "feature.txt").write_text("feature work")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "feature commit")

        adapter = ShellGitAdapter(repo_path=local)
        result = adapter.rebase(branch)

        assert result is True

    def test_rebase_returns_false_on_conflict(
        self,
        cloned_repo: tuple[Path, Path],
    ) -> None:
        from wiggum.git.shell import ShellGitAdapter

        _upstream, local = cloned_repo
        branch = _run_git(local, "rev-parse", "--abbrev-ref", "HEAD")
        # Create a feature branch that modifies the same file differently
        _run_git(local, "checkout", "-b", "feat/conflict-test")
        (local / "initial.txt").write_text("feature version")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "feature change")

        # Go back to main and make a conflicting change
        _run_git(local, "checkout", branch)
        (local / "initial.txt").write_text("main version")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "main change")

        # Switch to feature and rebase onto main -- should conflict
        _run_git(local, "checkout", "feat/conflict-test")
        adapter = ShellGitAdapter(repo_path=local)
        result = adapter.rebase(branch)

        assert result is False


class TestRebaseContinue:
    def test_rebase_continue_returns_true_after_conflict_resolution(
        self,
        cloned_repo: tuple[Path, Path],
    ) -> None:
        from wiggum.git.shell import ShellGitAdapter

        _upstream, local = cloned_repo
        branch = _run_git(local, "rev-parse", "--abbrev-ref", "HEAD")
        _run_git(local, "checkout", "-b", "feat/continue-test")
        (local / "initial.txt").write_text("feature version")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "feature change")

        _run_git(local, "checkout", branch)
        (local / "initial.txt").write_text("main version")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "main change")

        _run_git(local, "checkout", "feat/continue-test")
        subprocess.run(
            ["git", "rebase", branch],
            cwd=local,
            capture_output=True,
            check=False,
        )

        # Resolve the conflict and stage
        (local / "initial.txt").write_text("resolved version")
        _run_git(local, "add", "initial.txt")

        adapter = ShellGitAdapter(repo_path=local)
        result = adapter.rebase_continue()

        assert result is True

    def test_rebase_continue_returns_false_when_conflicts_remain(
        self,
        cloned_repo: tuple[Path, Path],
    ) -> None:
        from wiggum.git.shell import ShellGitAdapter

        _upstream, local = cloned_repo
        branch = _run_git(local, "rev-parse", "--abbrev-ref", "HEAD")

        # Create feature branch with two conflicting commits
        _run_git(local, "checkout", "-b", "feat/continue-fail")
        (local / "initial.txt").write_text("feature v1")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "feature change 1")
        (local / "initial.txt").write_text("feature v2")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "feature change 2")

        _run_git(local, "checkout", branch)
        (local / "initial.txt").write_text("main version")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "main change")

        _run_git(local, "checkout", "feat/continue-fail")
        subprocess.run(
            ["git", "rebase", branch],
            cwd=local,
            capture_output=True,
            check=False,
        )

        # Resolve first conflict but leave the second one for rebase --continue to hit
        (local / "initial.txt").write_text("resolved first")
        _run_git(local, "add", "initial.txt")

        adapter = ShellGitAdapter(repo_path=local)
        result = adapter.rebase_continue()

        assert result is False


class TestRebaseAbort:
    def test_rebase_abort_cleans_up_conflict(
        self,
        cloned_repo: tuple[Path, Path],
    ) -> None:
        from wiggum.git.shell import ShellGitAdapter

        _upstream, local = cloned_repo
        branch = _run_git(local, "rev-parse", "--abbrev-ref", "HEAD")
        _run_git(local, "checkout", "-b", "feat/abort-test")
        (local / "initial.txt").write_text("feature version")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "feature change")

        _run_git(local, "checkout", branch)
        (local / "initial.txt").write_text("main version")
        _run_git(local, "add", ".")
        _run_git(local, "commit", "-m", "main change")

        _run_git(local, "checkout", "feat/abort-test")
        # Start a conflicting rebase manually
        subprocess.run(
            ["git", "rebase", branch],
            cwd=local,
            capture_output=True,
            check=False,
        )

        adapter = ShellGitAdapter(repo_path=local)
        adapter.rebase_abort()

        # After abort, branch should be back to feat/abort-test
        current = _run_git(local, "rev-parse", "--abbrev-ref", "HEAD")
        assert current == "feat/abort-test"


class TestDefaultBranch:
    def test_reads_default_from_origin_head(
        self,
        cloned_repo: tuple[Path, Path],
    ) -> None:
        from wiggum.git.shell import ShellGitAdapter

        _upstream, local = cloned_repo
        adapter = ShellGitAdapter(repo_path=local)
        result = adapter.default_branch()

        # The clone should have origin/HEAD pointing to the default branch
        assert isinstance(result, str)
        assert len(result) > 0

    def test_falls_back_to_main(self, git_repo: Path) -> None:
        from wiggum.git.shell import ShellGitAdapter

        # git_repo has no remote, so origin/HEAD does not exist
        adapter = ShellGitAdapter(repo_path=git_repo)
        result = adapter.default_branch()

        assert result == "main"
