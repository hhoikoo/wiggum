from importlib.metadata import entry_points

import cyclopts
import pytest

from wiggum.cli import app


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
        app(["run", str(plan_file)], exit_on_error=False)

    def test_run_rejects_missing_plan_file(self, tmp_path):
        missing = tmp_path / "nonexistent.md"
        with pytest.raises((FileNotFoundError, SystemExit)):
            app(["run", str(missing)], exit_on_error=False)

    def test_run_requires_plan_argument(self):
        with pytest.raises(cyclopts.MissingArgumentError):
            app(["run"], exit_on_error=False)
