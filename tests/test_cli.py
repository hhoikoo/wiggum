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
    def test_plan_uses_config_defaults(self):
        from wiggum.cli import _apply_overrides
        from wiggum.config import Config

        result = _apply_overrides(
            Config(), max_iterations=None, model=None, mode="plan"
        )
        assert result.loop.max_plan_iterations == 5
        assert result.model.plan.name == ""

    def test_build_uses_config_defaults(self):
        from wiggum.cli import _apply_overrides
        from wiggum.config import Config

        result = _apply_overrides(
            Config(), max_iterations=None, model=None, mode="build"
        )
        assert result.loop.max_build_iterations == 20

    def test_cli_flag_overrides_plan_model(self):
        from wiggum.cli import _apply_overrides
        from wiggum.config import Config

        result = _apply_overrides(
            Config(), max_iterations=10, model="opus", mode="plan"
        )
        assert result.loop.max_plan_iterations == 10
        assert result.model.plan.name == "opus"
        assert result.model.build.name == ""

    def test_cli_flag_overrides_build_model(self):
        from wiggum.cli import _apply_overrides
        from wiggum.config import Config

        result = _apply_overrides(
            Config(), max_iterations=None, model="sonnet", mode="build"
        )
        assert result.model.build.name == "sonnet"
        assert result.model.plan.name == ""

    def test_combined_mode_overrides_both_models(self):
        from wiggum.cli import _apply_overrides
        from wiggum.config import Config

        result = _apply_overrides(
            Config(), max_iterations=None, model="haiku", mode="combined"
        )
        assert result.model.plan.name == "haiku"
        assert result.model.build.name == "haiku"

    def test_combined_mode_uses_build_iterations(self):
        from wiggum.cli import _apply_overrides
        from wiggum.config import Config

        result = _apply_overrides(
            Config(), max_iterations=None, model=None, mode="combined"
        )
        assert result.loop.max_build_iterations == 20
