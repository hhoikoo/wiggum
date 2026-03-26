"""Configuration loading and startup validation."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from pydantic import BaseModel, Field


class WiggumConfig(BaseModel, frozen=True):
    """Project-level configuration for a wiggum run."""

    batch_size: int = Field(default=10, gt=0)
    cycle_limit: int = Field(default=0, ge=0)
    max_turns: int = Field(default=50, gt=0)
    agent_timeout: int = Field(default=600, gt=0)
    base_branch: str | None = None


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
