from __future__ import annotations

from typing import TYPE_CHECKING

from wiggum.worktree import ensure_symlinks

if TYPE_CHECKING:
    from pathlib import Path


class TestEnsureSymlinksCreatesLinks:
    """Tests for ensure_symlinks creating symlinks from worktree into repo root."""

    def test_creates_symlink_for_single_directory(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        worktree = tmp_path / "worktree"
        repo_root.mkdir()
        worktree.mkdir()
        (repo_root / ".claude").mkdir()

        ensure_symlinks(repo_root, worktree, [".claude"])

        link = worktree / ".claude"
        assert link.is_symlink()
        assert link.resolve() == (repo_root / ".claude").resolve()

    def test_creates_symlinks_for_multiple_directories(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        worktree = tmp_path / "worktree"
        repo_root.mkdir()
        worktree.mkdir()
        (repo_root / ".claude").mkdir()
        (repo_root / ".wiggum").mkdir()

        ensure_symlinks(repo_root, worktree, [".claude", ".wiggum"])

        assert (worktree / ".claude").is_symlink()
        assert (worktree / ".wiggum").is_symlink()


class TestEnsureSymlinksSkipsWhenSourceMissing:
    """Tests for skipping symlink creation when source directory does not exist."""

    def test_skips_when_source_does_not_exist(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        worktree = tmp_path / "worktree"
        repo_root.mkdir()
        worktree.mkdir()

        ensure_symlinks(repo_root, worktree, [".nonexistent"])

        assert not (worktree / ".nonexistent").exists()

    def test_creates_existing_and_skips_missing(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        worktree = tmp_path / "worktree"
        repo_root.mkdir()
        worktree.mkdir()
        (repo_root / ".claude").mkdir()

        ensure_symlinks(repo_root, worktree, [".claude", ".nonexistent"])

        assert (worktree / ".claude").is_symlink()
        assert not (worktree / ".nonexistent").exists()


class TestEnsureSymlinksSkipsWhenTargetExists:
    """Tests for skipping symlink creation when target already exists in worktree."""

    def test_skips_when_target_is_existing_directory(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        worktree = tmp_path / "worktree"
        repo_root.mkdir()
        worktree.mkdir()
        (repo_root / ".claude").mkdir()
        (worktree / ".claude").mkdir()

        ensure_symlinks(repo_root, worktree, [".claude"])

        assert not (worktree / ".claude").is_symlink()

    def test_skips_when_target_is_existing_symlink(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        worktree = tmp_path / "worktree"
        repo_root.mkdir()
        worktree.mkdir()
        (repo_root / ".claude").mkdir()
        other_target = tmp_path / "other"
        other_target.mkdir()
        (worktree / ".claude").symlink_to(other_target)

        ensure_symlinks(repo_root, worktree, [".claude"])

        # Should not overwrite the existing symlink
        assert (worktree / ".claude").resolve() == other_target.resolve()

    def test_does_not_overwrite_existing_file(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        worktree = tmp_path / "worktree"
        repo_root.mkdir()
        worktree.mkdir()
        (repo_root / ".claude").mkdir()
        (worktree / ".claude").write_text("occupied")

        ensure_symlinks(repo_root, worktree, [".claude"])

        assert not (worktree / ".claude").is_symlink()
        assert (worktree / ".claude").read_text() == "occupied"


class TestEnsureSymlinksReturnValue:
    """Tests for ensure_symlinks return type."""

    def test_returns_none(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        worktree = tmp_path / "worktree"
        repo_root.mkdir()
        worktree.mkdir()

        result = ensure_symlinks(repo_root, worktree, [])

        assert result is None
