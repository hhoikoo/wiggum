"""Configuration loading and startup validation."""

import sys
import tomllib
from pathlib import Path

from pydantic import BaseModel, Field


class WorktreeConfig(BaseModel, frozen=True):
    """Worktree symlink configuration."""

    symlink_directories: list[str] = Field(default=[".wiggum", ".claude"])


class BuildConfig(BaseModel, frozen=True):
    """Build and verify command configuration."""

    setup_command: str | None = None
    verify_command: str | None = None


class WiggumConfig(BaseModel, frozen=True):
    """Project-level configuration for a wiggum run."""

    batch_size: int = Field(default=10, gt=0)
    cycle_limit: int = Field(default=0, ge=0)
    max_turns: int = Field(default=50, gt=0)
    agent_timeout: int = Field(default=600, gt=0)
    base_branch: str | None = None
    worktree: WorktreeConfig = Field(default_factory=WorktreeConfig)
    build: BuildConfig = Field(default_factory=BuildConfig)


def load_config(repo_path: Path) -> WiggumConfig:
    """Load configuration from .wiggum/config.toml or ~/.wiggum/config.toml."""
    project_cfg = repo_path / ".wiggum" / "config.toml"
    if project_cfg.is_file():
        data = tomllib.loads(project_cfg.read_text())
        return WiggumConfig(**data)

    home_cfg = Path.home() / ".wiggum" / "config.toml"
    if home_cfg.is_file():
        data = tomllib.loads(home_cfg.read_text())
        return WiggumConfig(**data)

    msg = "No .wiggum/config.toml found in project or home directory"
    raise FileNotFoundError(msg)


def validate_startup(*, repo_path: Path) -> None:
    """Check that repo_path is a git repo with a wiggum config, or exit."""
    if not (repo_path / ".git").is_dir():
        sys.exit("Fatal: not a git repository")

    if not (repo_path / ".wiggum" / "config.toml").is_file():
        sys.exit("Fatal: missing .wiggum/config.toml")


def get_build_config(repo_path: Path) -> dict[str, str | None]:
    """Extract the build section from config for agent consumption."""
    cfg = load_config(repo_path)
    return {
        "setup_command": cfg.build.setup_command,
        "verify_command": cfg.build.verify_command,
    }
