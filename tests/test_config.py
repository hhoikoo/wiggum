from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from wiggum.config import (
    BuildConfig,
    WiggumConfig,
    WorktreeConfig,
    get_build_config,
    validate_startup,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestWiggumConfigDefaults:
    """Tests for WiggumConfig default field values."""

    def test_batch_size_default(self) -> None:
        cfg = WiggumConfig()
        assert cfg.batch_size == 10

    def test_cycle_limit_default(self) -> None:
        cfg = WiggumConfig()
        assert cfg.cycle_limit == 0

    def test_max_turns_default(self) -> None:
        cfg = WiggumConfig()
        assert cfg.max_turns == 50

    def test_agent_timeout_default(self) -> None:
        cfg = WiggumConfig()
        assert cfg.agent_timeout == 600

    def test_base_branch_default_is_none(self) -> None:
        cfg = WiggumConfig()
        assert cfg.base_branch is None


class TestWiggumConfigCustomValues:
    """Tests for WiggumConfig with explicit field values."""

    def test_all_fields_set(self) -> None:
        cfg = WiggumConfig(
            batch_size=5,
            cycle_limit=3,
            max_turns=20,
            agent_timeout=300,
            base_branch="develop",
        )
        assert cfg.batch_size == 5
        assert cfg.cycle_limit == 3
        assert cfg.max_turns == 20
        assert cfg.agent_timeout == 300
        assert cfg.base_branch == "develop"

    def test_partial_override(self) -> None:
        cfg = WiggumConfig(batch_size=7)
        assert cfg.batch_size == 7
        assert cfg.cycle_limit == 0

    def test_base_branch_set_to_string(self) -> None:
        cfg = WiggumConfig(base_branch="main")
        assert cfg.base_branch == "main"

    def test_base_branch_explicit_none(self) -> None:
        cfg = WiggumConfig(base_branch=None)
        assert cfg.base_branch is None


class TestWiggumConfigValidation:
    """Tests for WiggumConfig field validation."""

    def test_batch_size_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            WiggumConfig(batch_size=0)

    def test_cycle_limit_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            WiggumConfig(cycle_limit=-1)

    def test_max_turns_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            WiggumConfig(max_turns=0)

    def test_agent_timeout_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            WiggumConfig(agent_timeout=0)


class TestWiggumConfigImmutability:
    """Tests for WiggumConfig frozen model behavior."""

    def test_frozen(self) -> None:
        cfg = WiggumConfig()
        with pytest.raises(ValidationError):
            cfg.batch_size = 99  # type: ignore[misc]


class TestWorktreeConfigDefaults:
    """Tests for WorktreeConfig default field values."""

    def test_symlink_directories_default(self) -> None:
        cfg = WorktreeConfig()
        assert cfg.symlink_directories == [".wiggum", ".claude"]

    def test_symlink_directories_default_is_list(self) -> None:
        cfg = WorktreeConfig()
        assert isinstance(cfg.symlink_directories, list)


class TestWorktreeConfigCustomValues:
    """Tests for WorktreeConfig with explicit field values."""

    def test_custom_symlink_directories(self) -> None:
        cfg = WorktreeConfig(symlink_directories=[".config", ".env"])
        assert cfg.symlink_directories == [".config", ".env"]

    def test_empty_symlink_directories(self) -> None:
        cfg = WorktreeConfig(symlink_directories=[])
        assert cfg.symlink_directories == []


class TestBuildConfigDefaults:
    """Tests for BuildConfig default field values."""

    def test_setup_command_default_is_none(self) -> None:
        cfg = BuildConfig()
        assert cfg.setup_command is None

    def test_verify_command_default_is_none(self) -> None:
        cfg = BuildConfig()
        assert cfg.verify_command is None


class TestBuildConfigCustomValues:
    """Tests for BuildConfig with explicit field values."""

    def test_setup_command_set(self) -> None:
        cfg = BuildConfig(setup_command="uv sync")
        assert cfg.setup_command == "uv sync"

    def test_verify_command_set(self) -> None:
        cfg = BuildConfig(verify_command="uv run pytest")
        assert cfg.verify_command == "uv run pytest"

    def test_both_commands_set(self) -> None:
        cfg = BuildConfig(setup_command="uv sync", verify_command="uv run pytest")
        assert cfg.setup_command == "uv sync"
        assert cfg.verify_command == "uv run pytest"

    def test_explicit_none_values(self) -> None:
        cfg = BuildConfig(setup_command=None, verify_command=None)
        assert cfg.setup_command is None
        assert cfg.verify_command is None


class TestWiggumConfigBuildSection:
    """Tests for build section on WiggumConfig."""

    def test_build_default_is_build_config(self) -> None:
        cfg = WiggumConfig()
        assert isinstance(cfg.build, BuildConfig)

    def test_build_default_setup_command_is_none(self) -> None:
        cfg = WiggumConfig()
        assert cfg.build.setup_command is None

    def test_build_default_verify_command_is_none(self) -> None:
        cfg = WiggumConfig()
        assert cfg.build.verify_command is None

    def test_build_custom_values(self) -> None:
        cfg = WiggumConfig(
            build=BuildConfig(setup_command="make", verify_command="make test")
        )
        assert cfg.build.setup_command == "make"
        assert cfg.build.verify_command == "make test"

    def test_build_frozen(self) -> None:
        cfg = WiggumConfig()
        with pytest.raises(ValidationError):
            cfg.build = BuildConfig()  # type: ignore[misc]


class TestWiggumConfigWorktreeSection:
    """Tests for worktree section on WiggumConfig."""

    def test_worktree_default_is_worktree_config(self) -> None:
        cfg = WiggumConfig()
        assert isinstance(cfg.worktree, WorktreeConfig)

    def test_worktree_default_symlink_directories(self) -> None:
        cfg = WiggumConfig()
        assert cfg.worktree.symlink_directories == [".wiggum", ".claude"]

    def test_worktree_custom_values(self) -> None:
        cfg = WiggumConfig(worktree=WorktreeConfig(symlink_directories=[".my_dir"]))
        assert cfg.worktree.symlink_directories == [".my_dir"]

    def test_worktree_frozen(self) -> None:
        cfg = WiggumConfig()
        with pytest.raises(ValidationError):
            cfg.worktree = WorktreeConfig()  # type: ignore[misc]


# -- load_config tests -------------------------------------------------------

PROJECT_TOML = "batch_size = 5\nmax_turns = 20\n"
PROJECT_TOML_WITH_BASE_BRANCH = 'batch_size = 5\nbase_branch = "develop"\n'
PROJECT_TOML_WITH_BUILD = 'batch_size = 5\n\n[build]\nsetup_command = "uv sync"\nverify_command = "uv run pytest"\n'
PROJECT_TOML_WITH_BUILD_PARTIAL = (
    'batch_size = 5\n\n[build]\nsetup_command = "make install"\n'
)
PROJECT_TOML_WITH_WORKTREE = (
    'batch_size = 5\n\n[worktree]\nsymlink_directories = [".config", ".env"]\n'
)
HOME_TOML = "batch_size = 3\nmax_turns = 30\n"


@pytest.fixture
def project_with_config(tmp_path: Path) -> Path:
    cfg_dir = tmp_path / ".wiggum"
    cfg_dir.mkdir()
    (cfg_dir / "config.toml").write_text(PROJECT_TOML)
    return tmp_path


@pytest.fixture
def home_with_config(tmp_path: Path) -> Path:
    home = tmp_path / "fakehome"
    cfg_dir = home / ".wiggum"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.toml").write_text(HOME_TOML)
    return home


class TestLoadConfigFromProject:
    def test_returns_wiggum_config(self, project_with_config: Path):
        from wiggum.config import load_config

        result = load_config(project_with_config)
        assert isinstance(result, WiggumConfig)

    def test_reads_project_values(self, project_with_config: Path):
        from wiggum.config import load_config

        cfg = load_config(project_with_config)
        assert cfg.batch_size == 5
        assert cfg.max_turns == 20

    def test_unset_fields_use_defaults(self, project_with_config: Path):
        from wiggum.config import load_config

        cfg = load_config(project_with_config)
        assert cfg.cycle_limit == 0
        assert cfg.agent_timeout == 600


class TestLoadConfigBaseBranch:
    def test_base_branch_loaded_from_toml(self, tmp_path: Path) -> None:
        from wiggum.config import load_config

        cfg_dir = tmp_path / ".wiggum"
        cfg_dir.mkdir()
        (cfg_dir / "config.toml").write_text(PROJECT_TOML_WITH_BASE_BRANCH)
        cfg = load_config(tmp_path)
        assert cfg.base_branch == "develop"

    def test_base_branch_defaults_to_none_when_omitted(
        self, project_with_config: Path
    ) -> None:
        from wiggum.config import load_config

        cfg = load_config(project_with_config)
        assert cfg.base_branch is None


class TestLoadConfigWorktreeSection:
    def test_worktree_loaded_from_toml(self, tmp_path: Path) -> None:
        from wiggum.config import load_config

        cfg_dir = tmp_path / ".wiggum"
        cfg_dir.mkdir()
        (cfg_dir / "config.toml").write_text(PROJECT_TOML_WITH_WORKTREE)
        cfg = load_config(tmp_path)
        assert cfg.worktree.symlink_directories == [".config", ".env"]

    def test_worktree_defaults_when_omitted(self, project_with_config: Path) -> None:
        from wiggum.config import load_config

        cfg = load_config(project_with_config)
        assert cfg.worktree.symlink_directories == [".wiggum", ".claude"]


class TestLoadConfigBuildSection:
    """Tests for loading [build] section from TOML."""

    def test_build_loaded_from_toml(self, tmp_path: Path) -> None:
        from wiggum.config import load_config

        cfg_dir = tmp_path / ".wiggum"
        cfg_dir.mkdir()
        (cfg_dir / "config.toml").write_text(PROJECT_TOML_WITH_BUILD)
        cfg = load_config(tmp_path)
        assert cfg.build.setup_command == "uv sync"
        assert cfg.build.verify_command == "uv run pytest"

    def test_build_partial_fields(self, tmp_path: Path) -> None:
        from wiggum.config import load_config

        cfg_dir = tmp_path / ".wiggum"
        cfg_dir.mkdir()
        (cfg_dir / "config.toml").write_text(PROJECT_TOML_WITH_BUILD_PARTIAL)
        cfg = load_config(tmp_path)
        assert cfg.build.setup_command == "make install"
        assert cfg.build.verify_command is None

    def test_build_defaults_when_omitted(self, project_with_config: Path) -> None:
        from wiggum.config import load_config

        cfg = load_config(project_with_config)
        assert cfg.build.setup_command is None
        assert cfg.build.verify_command is None


class TestLoadConfigFallback:
    def test_falls_back_to_home_config(
        self, tmp_path: Path, home_with_config: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from wiggum.config import load_config

        monkeypatch.setattr(
            "pathlib.Path.home",
            classmethod(lambda cls: home_with_config),
        )
        cfg = load_config(tmp_path)
        assert cfg.batch_size == 3
        assert cfg.max_turns == 30

    def test_project_config_preferred_over_home(
        self,
        project_with_config: Path,
        home_with_config: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        from wiggum.config import load_config

        monkeypatch.setattr(
            "pathlib.Path.home",
            classmethod(lambda cls: home_with_config),
        )
        cfg = load_config(project_with_config)
        assert cfg.batch_size == 5


class TestLoadConfigMissing:
    def test_raises_when_no_config_anywhere(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        from wiggum.config import load_config

        empty_home = tmp_path / "empty_home"
        empty_home.mkdir()
        monkeypatch.setattr(
            "pathlib.Path.home",
            classmethod(lambda cls: empty_home),
        )
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path)


# -- validate_startup tests --------------------------------------------------


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A tmp_path that looks like a git repository."""
    (tmp_path / ".git").mkdir()
    return tmp_path


@pytest.fixture
def git_repo_with_config(git_repo: Path) -> Path:
    """A git repo with a .wiggum/config.toml present."""
    cfg_dir = git_repo / ".wiggum"
    cfg_dir.mkdir()
    (cfg_dir / "config.toml").touch()
    return git_repo


class TestValidateStartupNotGitRepo:
    """Fatal error when repo_path is not a git repository."""

    def test_raises_system_exit(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".wiggum"
        cfg_dir.mkdir()
        (cfg_dir / "config.toml").touch()

        with pytest.raises(SystemExit):
            validate_startup(repo_path=tmp_path)

    def test_error_mentions_git(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".wiggum"
        cfg_dir.mkdir()
        (cfg_dir / "config.toml").touch()

        with pytest.raises(SystemExit, match=r"(?i)git"):
            validate_startup(repo_path=tmp_path)

    def test_error_is_fatal(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".wiggum"
        cfg_dir.mkdir()
        (cfg_dir / "config.toml").touch()

        with pytest.raises(SystemExit, match=r"(?i)fatal"):
            validate_startup(repo_path=tmp_path)


class TestValidateStartupNoConfig:
    """Fatal error when .wiggum/config.toml is missing."""

    def test_raises_system_exit(self, git_repo: Path) -> None:
        with pytest.raises(SystemExit):
            validate_startup(repo_path=git_repo)

    def test_error_mentions_config(self, git_repo: Path) -> None:
        with pytest.raises(SystemExit, match=r"(?i)config"):
            validate_startup(repo_path=git_repo)

    def test_error_is_fatal(self, git_repo: Path) -> None:
        with pytest.raises(SystemExit, match=r"(?i)fatal"):
            validate_startup(repo_path=git_repo)


class TestValidateStartupSuccess:
    """No error when both git repo and config exist."""

    def test_does_not_raise(self, git_repo_with_config: Path) -> None:
        validate_startup(repo_path=git_repo_with_config)

    def test_returns_none(self, git_repo_with_config: Path) -> None:
        result = validate_startup(repo_path=git_repo_with_config)
        assert result is None


# -- get_build_config tests --------------------------------------------------

_BUILD_TOML_BOTH = """\
[build]
setup_command = "uv sync"
verify_command = "uv run pytest"
"""

_BUILD_TOML_SETUP_ONLY = """\
[build]
setup_command = "make install"
"""

_BUILD_TOML_VERIFY_ONLY = """\
[build]
verify_command = "make test"
"""

_BUILD_TOML_EMPTY_SECTION = """\
[build]
"""

_TOML_NO_BUILD_SECTION = """\
batch_size = 5
"""


def _write_config(tmp_path: Path, content: str) -> Path:
    cfg_dir = tmp_path / ".wiggum"
    cfg_dir.mkdir(exist_ok=True)
    (cfg_dir / "config.toml").write_text(content)
    return tmp_path


class TestGetBuildConfigBothCommands:
    """Returns both commands when build section has both."""

    def test_returns_dict(self, tmp_path: Path) -> None:
        repo = _write_config(tmp_path, _BUILD_TOML_BOTH)
        result = get_build_config(repo)
        assert isinstance(result, dict)

    def test_setup_command(self, tmp_path: Path) -> None:
        repo = _write_config(tmp_path, _BUILD_TOML_BOTH)
        result = get_build_config(repo)
        assert result["setup_command"] == "uv sync"

    def test_verify_command(self, tmp_path: Path) -> None:
        repo = _write_config(tmp_path, _BUILD_TOML_BOTH)
        result = get_build_config(repo)
        assert result["verify_command"] == "uv run pytest"


class TestGetBuildConfigPartialCommands:
    """Missing commands default to None."""

    def test_setup_only_has_verify_none(self, tmp_path: Path) -> None:
        repo = _write_config(tmp_path, _BUILD_TOML_SETUP_ONLY)
        result = get_build_config(repo)
        assert result["setup_command"] == "make install"
        assert result["verify_command"] is None

    def test_verify_only_has_setup_none(self, tmp_path: Path) -> None:
        repo = _write_config(tmp_path, _BUILD_TOML_VERIFY_ONLY)
        result = get_build_config(repo)
        assert result["setup_command"] is None
        assert result["verify_command"] == "make test"


class TestGetBuildConfigNoBuildSection:
    """Both values are None when build section is absent or empty."""

    def test_no_build_section(self, tmp_path: Path) -> None:
        repo = _write_config(tmp_path, _TOML_NO_BUILD_SECTION)
        result = get_build_config(repo)
        assert result["setup_command"] is None
        assert result["verify_command"] is None

    def test_empty_build_section(self, tmp_path: Path) -> None:
        repo = _write_config(tmp_path, _BUILD_TOML_EMPTY_SECTION)
        result = get_build_config(repo)
        assert result["setup_command"] is None
        assert result["verify_command"] is None


class TestGetBuildConfigKeys:
    """Returned dict always has exactly the expected keys."""

    def test_keys_with_both_set(self, tmp_path: Path) -> None:
        repo = _write_config(tmp_path, _BUILD_TOML_BOTH)
        result = get_build_config(repo)
        assert set(result.keys()) == {"setup_command", "verify_command"}

    def test_keys_with_no_build_section(self, tmp_path: Path) -> None:
        repo = _write_config(tmp_path, _TOML_NO_BUILD_SECTION)
        result = get_build_config(repo)
        assert set(result.keys()) == {"setup_command", "verify_command"}
