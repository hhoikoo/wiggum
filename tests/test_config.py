import pytest
from pydantic import ValidationError

from wiggum.config import (
    Config,
    LoopConfig,
    ModelConfig,
    ModelPhaseConfig,
    find_config,
    load_config,
)


class TestLoopConfig:
    def test_defaults(self):
        cfg = LoopConfig()
        assert cfg.max_plan_iterations == 5
        assert cfg.max_build_iterations == 20
        assert cfg.quality_commands == []

    def test_custom_values(self):
        cfg = LoopConfig(
            max_plan_iterations=10,
            max_build_iterations=50,
            quality_commands=["uv run pytest"],
        )
        assert cfg.max_plan_iterations == 10
        assert cfg.max_build_iterations == 50
        assert cfg.quality_commands == ["uv run pytest"]

    def test_min_plan_iterations(self):
        with pytest.raises(ValidationError):
            LoopConfig(max_plan_iterations=0)

    def test_min_build_iterations(self):
        with pytest.raises(ValidationError):
            LoopConfig(max_build_iterations=0)


class TestModelConfig:
    def test_defaults(self):
        cfg = ModelConfig()
        assert cfg.name == ""
        assert cfg.flags == []

    def test_custom_values(self):
        cfg = ModelConfig(name="opus", flags=["--max-turns", "50"])
        assert cfg.name == "opus"
        assert cfg.flags == ["--max-turns", "50"]


class TestModelPhaseConfig:
    def test_defaults(self):
        cfg = ModelPhaseConfig()
        assert cfg.plan.name == ""
        assert cfg.build.name == ""

    def test_custom_values(self):
        cfg = ModelPhaseConfig(
            plan=ModelConfig(name="opus"),
            build=ModelConfig(name="sonnet", flags=["--max-turns", "50"]),
        )
        assert cfg.plan.name == "opus"
        assert cfg.build.name == "sonnet"
        assert cfg.build.flags == ["--max-turns", "50"]


class TestConfig:
    def test_defaults(self):
        cfg = Config()
        assert cfg.loop.max_plan_iterations == 5
        assert cfg.model.plan.name == ""
        assert cfg.model.build.name == ""

    def test_nested_from_dict(self):
        cfg = Config.model_validate(
            {
                "loop": {"max_plan_iterations": 3, "max_build_iterations": 10},
                "model": {"plan": {"name": "opus"}, "build": {"name": "sonnet"}},
            }
        )
        assert cfg.loop.max_plan_iterations == 3
        assert cfg.loop.max_build_iterations == 10
        assert cfg.model.plan.name == "opus"
        assert cfg.model.build.name == "sonnet"
        assert cfg.loop.quality_commands == []


class TestFindConfig:
    def test_finds_config_in_current_dir(self, tmp_path):
        (tmp_path / ".git").mkdir()
        config_dir = tmp_path / ".wiggum"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text("[loop]\nmax_plan_iterations = 3\n")

        result = find_config(start=tmp_path)
        assert result == config_file

    def test_finds_config_in_parent(self, tmp_path):
        (tmp_path / ".git").mkdir()
        config_dir = tmp_path / ".wiggum"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"
        config_file.write_text("[loop]\n")

        child = tmp_path / "src" / "pkg"
        child.mkdir(parents=True)

        result = find_config(start=child)
        assert result == config_file

    def test_returns_none_when_no_config(self, tmp_path):
        (tmp_path / ".git").mkdir()
        result = find_config(start=tmp_path)
        assert result is None

    def test_stops_at_git_sentinel(self, tmp_path):
        (tmp_path / ".git").mkdir()
        child = tmp_path / "subdir"
        child.mkdir()
        result = find_config(start=child)
        assert result is None

    def test_returns_none_at_filesystem_root(self, tmp_path):
        # No .git sentinel -- walks to root and returns None
        isolated = tmp_path / "no_git_here"
        isolated.mkdir()
        result = find_config(start=isolated)
        assert result is None


class TestLoadConfig:
    def test_loads_from_toml(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[loop]\n"
            "max_plan_iterations = 8\n"
            'quality_commands = ["uv run pytest"]\n'
            "\n"
            "[model.plan]\n"
            'name = "opus"\n'
            "\n"
            "[model.build]\n"
            'name = "sonnet"\n'
            'flags = ["--max-turns", "50"]\n'
        )
        cfg = load_config(path=config_file)
        assert cfg.loop.max_plan_iterations == 8
        assert cfg.loop.quality_commands == ["uv run pytest"]
        assert cfg.model.plan.name == "opus"
        assert cfg.model.build.name == "sonnet"
        assert cfg.model.build.flags == ["--max-turns", "50"]

    def test_falls_back_to_defaults(self, tmp_path, monkeypatch):
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        cfg = load_config(path=None)
        assert cfg == Config()

    def test_partial_toml_fills_defaults(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('[model.build]\nname = "sonnet"\n')
        cfg = load_config(path=config_file)
        assert cfg.model.build.name == "sonnet"
        assert cfg.model.plan.name == ""
        assert cfg.loop.max_plan_iterations == 5
        assert cfg.loop.max_build_iterations == 20

    def test_validation_error_on_bad_values(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[loop]\nmax_plan_iterations = 0\n")
        with pytest.raises(ValidationError):
            load_config(path=config_file)

    def test_nested_section_parsing(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            "[loop]\n"
            "max_plan_iterations = 2\n"
            "max_build_iterations = 15\n"
            'quality_commands = ["uv run pyright", "uv run ruff check src/"]\n'
        )
        cfg = load_config(path=config_file)
        assert cfg.loop.max_plan_iterations == 2
        assert cfg.loop.max_build_iterations == 15
        assert len(cfg.loop.quality_commands) == 2
