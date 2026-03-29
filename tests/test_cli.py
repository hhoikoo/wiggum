from unittest.mock import patch

from wiggum.cli import app, build, plan, run


class TestSubcommandRouting:
    def test_plan_subcommand_resolves(self):
        command, bound, _ = app.parse_args(["run", "plan", "42"])
        assert command is plan
        assert bound.arguments["issue_id"] == "42"

    def test_build_subcommand_resolves(self):
        command, bound, _ = app.parse_args(["run", "build", "42"])
        assert command is build
        assert bound.arguments["issue_id"] == "42"

    def test_default_run_resolves(self):
        command, bound, _ = app.parse_args(["run", "42"])
        assert command is run
        assert bound.arguments["issue_id"] == "42"


class TestArgumentParsing:
    def test_plan_with_max_iterations(self):
        _, bound, _ = app.parse_args(["run", "plan", "99", "--max-iterations", "10"])
        assert bound.arguments["issue_id"] == "99"
        assert bound.arguments["max_iterations"] == 10

    def test_plan_with_model(self):
        _, bound, _ = app.parse_args(["run", "plan", "99", "--model", "opus"])
        assert bound.arguments["model"] == "opus"

    def test_build_with_max_iterations(self):
        _, bound, _ = app.parse_args(["run", "build", "7", "--max-iterations", "25"])
        assert bound.arguments["max_iterations"] == 25

    def test_build_with_model(self):
        _, bound, _ = app.parse_args(["run", "build", "7", "--model", "sonnet"])
        assert bound.arguments["model"] == "sonnet"

    def test_default_run_with_all_flags(self):
        _, bound, _ = app.parse_args(
            ["run", "55", "--max-iterations", "3", "--model", "haiku"]
        )
        assert bound.arguments["issue_id"] == "55"
        assert bound.arguments["max_iterations"] == 3
        assert bound.arguments["model"] == "haiku"

    def test_plan_defaults_none_when_flags_omitted(self):
        _, bound, _ = app.parse_args(["run", "plan", "1"])
        assert bound.arguments.get("max_iterations") is None
        assert bound.arguments.get("model") is None


class TestConfigOverrides:
    @patch("wiggum.cli.load_config")
    def test_plan_uses_config_defaults(self, mock_load):
        from wiggum.config import Config

        mock_load.return_value = Config()
        from wiggum.cli import _resolve_config

        result = _resolve_config(max_iterations=None, model=None, mode="plan")
        assert result["max_iterations"] == 5
        assert result["model"] == ""

    @patch("wiggum.cli.load_config")
    def test_build_uses_config_defaults(self, mock_load):
        from wiggum.config import Config

        mock_load.return_value = Config()
        from wiggum.cli import _resolve_config

        result = _resolve_config(max_iterations=None, model=None, mode="build")
        assert result["max_iterations"] == 20

    @patch("wiggum.cli.load_config")
    def test_cli_flag_overrides_config(self, mock_load):
        from wiggum.config import Config

        mock_load.return_value = Config()
        from wiggum.cli import _resolve_config

        result = _resolve_config(max_iterations=10, model="opus", mode="plan")
        assert result["max_iterations"] == 10
        assert result["model"] == "opus"

    @patch("wiggum.cli.load_config")
    def test_combined_mode_uses_build_iterations(self, mock_load):
        from wiggum.config import Config

        mock_load.return_value = Config()
        from wiggum.cli import _resolve_config

        result = _resolve_config(max_iterations=None, model=None, mode="combined")
        assert result["max_iterations"] == 20
