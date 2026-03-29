"""Tests for the runner module -- plan mode loop."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from wiggum.config import Config, LoopConfig, ModelConfig
from wiggum.runner import resolve_specs, run_plan
from wiggum.subprocess_util import InvokeResult


def _setup_repo(tmp_path: Path, issue_id: str = "42") -> Path:
    """Create a minimal repo structure with .git, specs, and impl dirs."""
    (tmp_path / ".git").mkdir()
    specs = tmp_path / ".wiggum" / "specs" / issue_id
    specs.mkdir(parents=True)
    (specs / "prd.md").write_text("# PRD\nSome spec content")
    impl = tmp_path / ".wiggum" / "implementation" / issue_id
    impl.mkdir(parents=True)
    return tmp_path


class TestResolveSpecs:
    def test_reads_spec_files(self, tmp_path: Path):
        root = _setup_repo(tmp_path)
        content = resolve_specs("42", root=root)
        assert "Some spec content" in content

    def test_concatenates_multiple_files(self, tmp_path: Path):
        root = _setup_repo(tmp_path)
        specs = root / ".wiggum" / "specs" / "42"
        (specs / "notes.md").write_text("Extra notes")
        content = resolve_specs("42", root=root)
        assert "Extra notes" in content
        assert "Some spec content" in content

    def test_exits_when_specs_missing(self, tmp_path: Path):
        root = _setup_repo(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            resolve_specs("999", root=root)
        assert exc_info.value.code == 2

    def test_exits_when_not_git_repo(self, tmp_path: Path):
        with pytest.raises(SystemExit) as exc_info:
            resolve_specs("42", root=tmp_path)
        assert exc_info.value.code == 2


class TestRunPlan:
    @patch("wiggum.runner.invoke_claude")
    def test_early_exit_on_complete(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(
            stdout='Some text\n```json\n{"status": "complete"}\n```\n',
            exit_code=0,
        )
        cfg = Config(loop=LoopConfig(max_plan_iterations=5))

        code = run_plan("42", config=cfg, root=root)

        assert code == 0
        assert mock_invoke.call_count == 1

    @patch("wiggum.runner.invoke_claude")
    def test_max_iterations_reached(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(
            stdout='```json\n{"status": "in_progress"}\n```',
            exit_code=0,
        )
        cfg = Config(loop=LoopConfig(max_plan_iterations=3))

        code = run_plan("42", config=cfg, root=root)

        assert code == 1
        assert mock_invoke.call_count == 3

    @patch("wiggum.runner.invoke_claude")
    def test_missing_json_treated_as_in_progress(
        self, mock_invoke: MagicMock, tmp_path: Path
    ):
        root = _setup_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(
            stdout="No JSON here, just text.",
            exit_code=0,
        )
        cfg = Config(loop=LoopConfig(max_plan_iterations=2))

        code = run_plan("42", config=cfg, root=root)

        assert code == 1
        assert mock_invoke.call_count == 2

    @patch("wiggum.runner.invoke_claude")
    def test_creates_skeleton_files(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(
            stdout='```json\n{"status": "complete"}\n```',
            exit_code=0,
        )
        cfg = Config(loop=LoopConfig(max_plan_iterations=1))

        run_plan("42", config=cfg, root=root)

        impl = root / ".wiggum" / "implementation" / "42"
        assert (impl / "IMPLEMENTATION_PLAN.md").exists()
        assert (impl / "PROGRESS.md").exists()

    def test_exits_when_impl_dir_missing(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        specs = tmp_path / ".wiggum" / "specs" / "42"
        specs.mkdir(parents=True)
        (specs / "prd.md").write_text("spec")
        cfg = Config()

        with pytest.raises(SystemExit) as exc_info:
            run_plan("42", config=cfg, root=tmp_path)
        assert exc_info.value.code == 2

    def test_exits_when_specs_dir_missing(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        impl = tmp_path / ".wiggum" / "implementation" / "42"
        impl.mkdir(parents=True)
        cfg = Config()

        with pytest.raises(SystemExit) as exc_info:
            run_plan("42", config=cfg, root=tmp_path)
        assert exc_info.value.code == 2

    @patch("wiggum.runner.invoke_claude")
    def test_passes_model_config(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(
            stdout='```json\n{"status": "complete"}\n```',
            exit_code=0,
        )
        cfg = Config(model=ModelConfig(name="opus"))

        run_plan("42", config=cfg, root=root)

        _, kwargs = mock_invoke.call_args
        assert kwargs["model"].name == "opus"

    @patch("wiggum.runner.invoke_claude")
    def test_no_model_when_name_empty(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(
            stdout='```json\n{"status": "complete"}\n```',
            exit_code=0,
        )
        cfg = Config(model=ModelConfig(name=""))

        run_plan("42", config=cfg, root=root)

        _, kwargs = mock_invoke.call_args
        assert kwargs["model"] is None

    @patch("wiggum.runner.invoke_claude")
    def test_early_exit_after_multiple_in_progress(
        self, mock_invoke: MagicMock, tmp_path: Path
    ):
        root = _setup_repo(tmp_path)
        mock_invoke.side_effect = [
            InvokeResult(stdout='```json\n{"status": "in_progress"}\n```', exit_code=0),
            InvokeResult(stdout='```json\n{"status": "in_progress"}\n```', exit_code=0),
            InvokeResult(stdout='```json\n{"status": "complete"}\n```', exit_code=0),
        ]
        cfg = Config(loop=LoopConfig(max_plan_iterations=5))

        code = run_plan("42", config=cfg, root=root)

        assert code == 0
        assert mock_invoke.call_count == 3
