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
            patch("wiggum.cli.inner_loop"),
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
    """Tests that run wires startup validation, config, and loop entry."""

    def _setup_repo(self, tmp_path):
        """Create a minimal plan file and .wiggum/config.toml."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n\n### Section\n- [ ] item\n")
        return plan_file

    def test_run_calls_validate_startup(self, tmp_path):
        plan_file = self._setup_repo(tmp_path)
        with (
            patch("wiggum.cli.validate_startup") as mock_validate,
            patch("wiggum.cli.load_config", return_value=WiggumConfig()),
            patch("wiggum.cli.inner_loop"),
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
            patch("wiggum.cli.inner_loop"),
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            app(["run", str(plan_file)], exit_on_error=False)

        mock_load.assert_called_once_with(tmp_path)

    def test_run_calls_inner_loop_with_correct_args(self, tmp_path):
        plan_file = self._setup_repo(tmp_path)
        config = WiggumConfig(batch_size=5)
        with (
            patch("wiggum.cli.validate_startup"),
            patch("wiggum.cli.load_config", return_value=config),
            patch("wiggum.cli.inner_loop") as mock_loop,
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
            patch("wiggum.cli.inner_loop"),
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
            patch("wiggum.cli.inner_loop"),
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
            patch("wiggum.cli.inner_loop") as mock_loop,
            patch("wiggum.cli.SubprocessGit") as mock_git_cls,
            patch("wiggum.cli.SubprocessAgent"),
        ):
            mock_git_cls.return_value.repo_root.return_value = tmp_path
            with pytest.raises(SystemExit):
                app(["run", str(plan_file)], exit_on_error=False)

        mock_load.assert_not_called()
        mock_loop.assert_not_called()
