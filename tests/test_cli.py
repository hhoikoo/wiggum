from importlib.metadata import entry_points
from unittest.mock import patch

import cyclopts
import pytest

from wiggum.cli import app
from wiggum.config import WiggumConfig


class TestEntryPoint:
    def test_wiggum_console_script_registered(self):
        eps = entry_points(group="console_scripts", name="wiggum")
        assert len(eps) == 1
        ep = next(iter(eps))
        assert ep.value == "wiggum.cli:app"


class TestAppInstance:
    def test_app_is_cyclopts_app(self):
        assert isinstance(app, cyclopts.App)


class TestRunSubcommand:
    def test_run_accepts_plan_path(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n\n### Section\n- [ ] item\n")
        with (
            patch("wiggum.cli.validate_startup"),
            patch("wiggum.cli.load_config", return_value=WiggumConfig()),
            patch("wiggum.cli.outer_loop"),
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            app(["run", str(plan_file)], exit_on_error=False)

    def test_run_rejects_missing_plan_file(self, tmp_path):
        missing = tmp_path / "nonexistent.md"
        with pytest.raises((FileNotFoundError, SystemExit)):
            app(["run", str(missing)], exit_on_error=False)

    def test_run_requires_plan_argument(self):
        with pytest.raises(cyclopts.MissingArgumentError):
            app(["run"], exit_on_error=False)


class TestRunWiring:
    """Tests that run wires startup validation, config, and outer loop entry."""

    def _setup_repo(self, tmp_path):
        """Create a minimal plan file."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n\n### Section\n- [ ] item\n")
        return plan_file

    def test_run_calls_validate_startup(self, tmp_path):
        plan_file = self._setup_repo(tmp_path)
        with (
            patch("wiggum.cli.validate_startup") as mock_validate,
            patch("wiggum.cli.load_config", return_value=WiggumConfig()),
            patch("wiggum.cli.outer_loop"),
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            app(["run", str(plan_file)], exit_on_error=False)

        mock_validate.assert_called_once_with(repo_path=tmp_path)

    def test_run_calls_load_config_with_repo_root(self, tmp_path):
        plan_file = self._setup_repo(tmp_path)
        with (
            patch("wiggum.cli.validate_startup"),
            patch("wiggum.cli.load_config", return_value=WiggumConfig()) as mock_load,
            patch("wiggum.cli.outer_loop"),
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            app(["run", str(plan_file)], exit_on_error=False)

        mock_load.assert_called_once_with(tmp_path)

    def test_run_calls_outer_loop_with_correct_args(self, tmp_path):
        plan_file = self._setup_repo(tmp_path)
        config = WiggumConfig(batch_size=5)
        with (
            patch("wiggum.cli.validate_startup"),
            patch("wiggum.cli.load_config", return_value=config),
            patch("wiggum.cli.outer_loop") as mock_loop,
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent") as mock_agent_cls,
        ):
            mock_git = mock_git_cls.return_value
            mock_git.repo_root.return_value = tmp_path
            mock_agent = mock_agent_cls.return_value
            app(["run", str(plan_file)], exit_on_error=False)

        mock_loop.assert_called_once_with(
            plan_path=plan_file,
            agent=mock_agent,
            git=mock_git,
            config=config,
        )

    def test_run_constructs_git_adapter(self, tmp_path):
        plan_file = self._setup_repo(tmp_path)
        with (
            patch("wiggum.cli.validate_startup"),
            patch("wiggum.cli.load_config", return_value=WiggumConfig()),
            patch("wiggum.cli.outer_loop"),
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            app(["run", str(plan_file)], exit_on_error=False)

        mock_git_cls.assert_called_once()

    def test_run_constructs_agent_adapter_with_repo_root(self, tmp_path):
        plan_file = self._setup_repo(tmp_path)
        with (
            patch("wiggum.cli.validate_startup"),
            patch("wiggum.cli.load_config", return_value=WiggumConfig()),
            patch("wiggum.cli.outer_loop"),
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent") as mock_agent_cls,
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            app(["run", str(plan_file)], exit_on_error=False)

        mock_agent_cls.assert_called_once_with(work_dir=tmp_path)

    def test_run_exits_when_validate_startup_fails(self, tmp_path):
        plan_file = self._setup_repo(tmp_path)
        with (
            patch(
                "wiggum.cli.validate_startup",
                side_effect=SystemExit("Fatal: not a git repository"),
            ),
            patch("wiggum.cli.load_config") as mock_load,
            patch("wiggum.cli.outer_loop") as mock_loop,
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            with pytest.raises(SystemExit):
                app(["run", str(plan_file)], exit_on_error=False)

        mock_load.assert_not_called()
        mock_loop.assert_not_called()

    def test_run_does_not_call_inner_loop_directly(self, tmp_path):
        plan_file = self._setup_repo(tmp_path)
        with (
            patch("wiggum.cli.validate_startup"),
            patch("wiggum.cli.load_config", return_value=WiggumConfig()),
            patch("wiggum.cli.outer_loop"),
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
            patch("wiggum.loop.inner_loop") as mock_inner,
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            app(["run", str(plan_file)], exit_on_error=False)

        mock_inner.assert_not_called()


_PLAN_WITH_CHECKED = """\
# Plan

### Section A
- [x] completed item one
- [ ] pending item two
- [x] completed item three

### Section B
- [ ] pending item four
"""

_PLAN_NO_CHECKED = """\
# Plan

### Section A
- [ ] pending item one
- [ ] pending item two
"""

_PLAN_ALL_CHECKED = """\
# Plan

### Section A
- [x] completed item one
- [x] completed item two

### Section B
- [x] completed item three
"""

_PLAN_EMPTY_SECTIONS = """\
# Plan

### Section A
"""


class TestSigintHandler:
    """Tests that SIGINT during run resets checked items and exits 130."""

    def _run_with_interrupt(self, tmp_path, plan_content):
        """Run CLI with outer_loop raising KeyboardInterrupt, return (plan_file, exit_code)."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)
        exit_code = None
        with (
            patch("wiggum.cli.validate_startup"),
            patch("wiggum.cli.load_config", return_value=WiggumConfig()),
            patch("wiggum.cli.outer_loop", side_effect=KeyboardInterrupt),
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            try:
                app(["run", str(plan_file)], exit_on_error=False)
            except SystemExit as exc:
                exit_code = exc.code
            except KeyboardInterrupt:
                pass
        return plan_file, exit_code

    def test_sigint_resets_checked_items_in_plan(self, tmp_path):
        plan_file, _ = self._run_with_interrupt(tmp_path, _PLAN_WITH_CHECKED)
        content = plan_file.read_text()
        assert "[x]" not in content
        assert "[X]" not in content
        assert "[ ] completed item one" in content
        assert "[ ] completed item three" in content

    def test_sigint_preserves_unchecked_items(self, tmp_path):
        plan_file, _ = self._run_with_interrupt(tmp_path, _PLAN_WITH_CHECKED)
        content = plan_file.read_text()
        assert "[ ] pending item two" in content
        assert "[ ] pending item four" in content

    def test_sigint_exits_with_code_130(self, tmp_path):
        _, exit_code = self._run_with_interrupt(tmp_path, _PLAN_WITH_CHECKED)
        assert exit_code == 130

    def test_sigint_idempotent_no_checked_items(self, tmp_path):
        plan_file, exit_code = self._run_with_interrupt(tmp_path, _PLAN_NO_CHECKED)
        assert exit_code == 130
        assert plan_file.read_text() == _PLAN_NO_CHECKED


class TestSigintHandlerIdempotency:
    """Tests that the SIGINT handler is safe to invoke multiple times."""

    def _run_with_interrupt(self, tmp_path, plan_content):
        """Run CLI with outer_loop raising KeyboardInterrupt, return (plan_file, exit_code)."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(plan_content)
        exit_code = None
        with (
            patch("wiggum.cli.validate_startup"),
            patch("wiggum.cli.load_config", return_value=WiggumConfig()),
            patch("wiggum.cli.outer_loop", side_effect=KeyboardInterrupt),
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            try:
                app(["run", str(plan_file)], exit_on_error=False)
            except SystemExit as exc:
                exit_code = exc.code
            except KeyboardInterrupt:
                pass
        return plan_file, exit_code

    def test_second_interrupt_produces_same_result_as_first(self, tmp_path):
        """Resetting an already-reset plan is a no-op."""
        plan_file, _ = self._run_with_interrupt(tmp_path, _PLAN_WITH_CHECKED)
        after_first = plan_file.read_text()

        _, exit_code = self._run_with_interrupt(tmp_path, after_first)
        after_second = plan_file.read_text()

        assert after_first == after_second
        assert exit_code == 130

    def test_interrupt_on_all_checked_plan_resets_all(self, tmp_path):
        """All checked items become unchecked after interrupt."""
        plan_file, exit_code = self._run_with_interrupt(tmp_path, _PLAN_ALL_CHECKED)
        content = plan_file.read_text()
        assert "[x]" not in content
        assert "[ ] completed item one" in content
        assert "[ ] completed item two" in content
        assert "[ ] completed item three" in content
        assert exit_code == 130

    def test_interrupt_twice_on_all_checked_is_stable(self, tmp_path):
        """After first interrupt resets all items, second leaves plan unchanged."""
        plan_file, _ = self._run_with_interrupt(tmp_path, _PLAN_ALL_CHECKED)
        after_first = plan_file.read_text()

        _, exit_code = self._run_with_interrupt(tmp_path, after_first)
        after_second = plan_file.read_text()

        assert after_first == after_second
        assert exit_code == 130

    def test_interrupt_on_empty_section_plan(self, tmp_path):
        """Handler on a plan with sections but no items does not error."""
        plan_file, exit_code = self._run_with_interrupt(tmp_path, _PLAN_EMPTY_SECTIONS)
        assert plan_file.read_text() == _PLAN_EMPTY_SECTIONS
        assert exit_code == 130
