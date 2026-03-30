import pytest

from wiggum.impl_dir import (
    create_skeleton_files,
    impl_dir_path,
    resolve_plan_path,
    resolve_progress_path,
    validate_impl_dir,
)


class TestImplDirPath:
    def test_returns_path_relative_to_root(self, tmp_path):
        (tmp_path / ".git").mkdir()
        result = impl_dir_path("42", root=tmp_path)
        assert result == tmp_path / ".wiggum" / "implementation" / "42"

    def test_exits_when_no_git_root(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            impl_dir_path("42", root=None)
        assert exc_info.value.code == 2


class TestValidateImplDir:
    def test_returns_path_when_exists(self, tmp_path):
        (tmp_path / ".git").mkdir()
        impl = tmp_path / ".wiggum" / "implementation" / "42"
        impl.mkdir(parents=True)
        result = validate_impl_dir("42", root=tmp_path)
        assert result == impl

    def test_exits_when_missing(self, tmp_path):
        (tmp_path / ".git").mkdir()
        with pytest.raises(SystemExit) as exc_info:
            validate_impl_dir("42", root=tmp_path)
        assert exc_info.value.code == 2


class TestCreateSkeletonFiles:
    def test_creates_both_files(self, tmp_path):
        create_skeleton_files(tmp_path)

        plan = tmp_path / "IMPLEMENTATION_PLAN.md"
        progress = tmp_path / "PROGRESS.md"
        assert plan.exists()
        assert progress.exists()

    def test_plan_has_title_and_checkbox_section(self, tmp_path):
        create_skeleton_files(tmp_path)
        content = (tmp_path / "IMPLEMENTATION_PLAN.md").read_text()
        assert "# Implementation Plan" in content
        assert "## Tasks" in content

    def test_progress_has_title(self, tmp_path):
        create_skeleton_files(tmp_path)
        content = (tmp_path / "PROGRESS.md").read_text()
        assert "# Progress" in content

    def test_does_not_overwrite_existing(self, tmp_path):
        plan = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan.write_text("existing plan")
        progress = tmp_path / "PROGRESS.md"
        progress.write_text("existing progress")

        create_skeleton_files(tmp_path)

        assert plan.read_text() == "existing plan"
        assert progress.read_text() == "existing progress"


class TestPathResolution:
    def test_resolve_plan_path(self, tmp_path):
        result = resolve_plan_path(tmp_path)
        assert result == tmp_path / "IMPLEMENTATION_PLAN.md"

    def test_resolve_progress_path(self, tmp_path):
        result = resolve_progress_path(tmp_path)
        assert result == tmp_path / "PROGRESS.md"
