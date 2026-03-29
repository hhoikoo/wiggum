"""Wiggum configuration with TOML loading and directory discovery."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field


class LoopConfig(BaseModel):
    """Loop iteration limits and quality gate commands."""

    max_plan_iterations: int = Field(default=5, ge=1)
    max_build_iterations: int = Field(default=20, ge=1)
    quality_commands: list[str] = Field(default_factory=list)


class ModelConfig(BaseModel):
    """Claude model selection and extra CLI flags."""

    name: str = ""
    flags: list[str] = Field(default_factory=list)


class Config(BaseModel):
    """Top-level configuration aggregating all sections."""

    loop: LoopConfig = Field(default_factory=LoopConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)


_CONFIG_PATH = Path(".wiggum") / "config.toml"
_SENTINEL = ".git"


def find_config(*, start: Path | None = None) -> Path | None:
    """Walk upward from *start* (default: cwd) looking for .wiggum/config.toml.

    Stops at the first directory containing a .git sentinel. Returns ``None``
    when no config file is found.
    """
    current = (start or Path.cwd()).resolve()
    while True:
        candidate = current / _CONFIG_PATH
        if candidate.is_file():
            return candidate
        if (current / _SENTINEL).exists():
            return None
        parent = current.parent
        if parent == current:
            return None
        current = parent


def load_config(*, path: Path | None = None) -> Config:
    """Load configuration from a TOML file, falling back to defaults.

    When *path* is ``None``, :func:`find_config` is used to discover the file.
    If no file is found, sensible defaults are returned.
    """
    resolved = path or find_config()
    if resolved is None:
        return Config()
    text = resolved.read_bytes()
    data = tomllib.loads(text.decode())
    return Config.model_validate(data)
