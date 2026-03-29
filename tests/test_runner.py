"""Tests for the runner module -- plan and build mode loops."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from wiggum.config import Config, LoopConfig, ModelConfig
from wiggum.runner import resolve_specs, run_build, run_plan
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


_PLAN_TWO_TASKS = """\
# Implementation Plan

## Tasks

- [ ] Implement the widget
- [ ] Write tests for the widget
"""

_PLAN_ALL_DONE = """\
# Implementation Plan

## Tasks

- [x] Implement the widget
- [x] Write tests for the widget
"""


def _setup_build_repo(
    tmp_path: Path,
    issue_id: str = "42",
    plan_content: str = _PLAN_TWO_TASKS,
) -> Path:
    """Create a minimal repo with .git, impl dir, plan, and progress files."""
    (tmp_path / ".git").mkdir()
    impl = tmp_path / ".wiggum" / "implementation" / issue_id
    impl.mkdir(parents=True)
    (impl / "IMPLEMENTATION_PLAN.md").write_text(plan_content)
    (impl / "PROGRESS.md").write_text("# Progress\n\n")
    return tmp_path


class TestRunBuild:
    @patch("wiggum.runner.invoke_claude")
    def test_completes_all_tasks(
        self, mock_invoke: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ):
        root = _setup_build_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(stdout="done", exit_code=0)
        cfg = Config(loop=LoopConfig(max_build_iterations=10))

        code = run_build("42", config=cfg, root=root)

        assert code == 0
        assert mock_invoke.call_count == 2
        summary = json.loads(capsys.readouterr().out)
        assert summary["all_complete"] is True
        assert summary["completed_tasks"] == 2
        assert summary["total_tasks"] == 2

    @patch("wiggum.runner.invoke_claude")
    def test_max_iterations_reached(
        self, mock_invoke: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ):
        root = _setup_build_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(stdout="done", exit_code=0)
        cfg = Config(loop=LoopConfig(max_build_iterations=1))

        code = run_build("42", config=cfg, root=root)

        assert code == 1
        assert mock_invoke.call_count == 1
        summary = json.loads(capsys.readouterr().out)
        assert summary["all_complete"] is False
        assert summary["completed_tasks"] == 1

    @patch("wiggum.runner.invoke_claude")
    def test_exits_zero_when_all_already_complete(
        self, mock_invoke: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ):
        root = _setup_build_repo(tmp_path, plan_content=_PLAN_ALL_DONE)
        cfg = Config(loop=LoopConfig(max_build_iterations=5))

        code = run_build("42", config=cfg, root=root)

        assert code == 0
        mock_invoke.assert_not_called()
        summary = json.loads(capsys.readouterr().out)
        assert summary["all_complete"] is True
        assert summary["completed_tasks"] == 0

    def test_exits_when_plan_missing(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        impl = tmp_path / ".wiggum" / "implementation" / "42"
        impl.mkdir(parents=True)
        cfg = Config()

        with pytest.raises(SystemExit) as exc_info:
            run_build("42", config=cfg, root=tmp_path)
        assert exc_info.value.code == 2

    def test_exits_when_impl_dir_missing(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        cfg = Config()

        with pytest.raises(SystemExit) as exc_info:
            run_build("42", config=cfg, root=tmp_path)
        assert exc_info.value.code == 2

    @patch("wiggum.runner.invoke_claude")
    def test_marks_tasks_in_plan_file(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_build_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(stdout="done", exit_code=0)
        cfg = Config(loop=LoopConfig(max_build_iterations=1))

        run_build("42", config=cfg, root=root)

        plan_text = (
            root / ".wiggum" / "implementation" / "42" / "IMPLEMENTATION_PLAN.md"
        ).read_text()
        assert "- [x] Implement the widget" in plan_text
        assert "- [ ] Write tests for the widget" in plan_text

    @patch("wiggum.runner.invoke_claude")
    def test_appends_to_progress_file(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_build_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(stdout="done", exit_code=0)
        cfg = Config(loop=LoopConfig(max_build_iterations=1))

        run_build("42", config=cfg, root=root)

        progress_text = (
            root / ".wiggum" / "implementation" / "42" / "PROGRESS.md"
        ).read_text()
        assert "## Iteration 1" in progress_text
        assert "Implement the widget" in progress_text
        assert "pass" in progress_text

    @patch("wiggum.runner.invoke_claude")
    def test_records_fail_outcome_on_nonzero_exit(
        self, mock_invoke: MagicMock, tmp_path: Path
    ):
        root = _setup_build_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(stdout="error", exit_code=1)
        cfg = Config(loop=LoopConfig(max_build_iterations=1))

        run_build("42", config=cfg, root=root)

        progress_text = (
            root / ".wiggum" / "implementation" / "42" / "PROGRESS.md"
        ).read_text()
        assert "fail" in progress_text

    @patch("wiggum.runner.invoke_claude")
    def test_passes_quality_commands(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_build_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(stdout="done", exit_code=0)
        cfg = Config(
            loop=LoopConfig(
                max_build_iterations=1,
                quality_commands=["uv run pytest", "uv run pyright"],
            )
        )

        run_build("42", config=cfg, root=root)

        prompt = mock_invoke.call_args[0][0]
        assert "uv run pytest" in prompt
        assert "uv run pyright" in prompt

    @patch("wiggum.runner.invoke_claude")
    def test_passes_model_config(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_build_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(stdout="done", exit_code=0)
        cfg = Config(model=ModelConfig(name="opus"))

        run_build("42", config=cfg, root=root)

        _, kwargs = mock_invoke.call_args
        assert kwargs["model"].name == "opus"

    @patch("wiggum.runner.invoke_claude")
    def test_no_model_when_name_empty(self, mock_invoke: MagicMock, tmp_path: Path):
        root = _setup_build_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(stdout="done", exit_code=0)
        cfg = Config(model=ModelConfig(name=""))

        run_build("42", config=cfg, root=root)

        _, kwargs = mock_invoke.call_args
        assert kwargs["model"] is None

    @patch("wiggum.runner.invoke_claude")
    def test_json_summary_structure(
        self, mock_invoke: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ):
        root = _setup_build_repo(tmp_path)
        mock_invoke.return_value = InvokeResult(stdout="done", exit_code=0)
        cfg = Config(loop=LoopConfig(max_build_iterations=10))

        run_build("42", config=cfg, root=root)

        summary = json.loads(capsys.readouterr().out)
        assert summary == {
            "issue_id": "42",
            "completed_tasks": 2,
            "total_tasks": 2,
            "all_complete": True,
            "exit_code": 0,
        }
