"""Tests that required project dependencies are declared in pyproject.toml."""

import tomllib
from pathlib import Path


def _load_dependencies() -> list[str]:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["dependencies"]


def test_cyclopts_in_dependencies():
    deps = _load_dependencies()
    matches = [d for d in deps if d.startswith("cyclopts")]
    assert matches, "cyclopts must be declared in [project] dependencies"


def test_pydantic_in_dependencies():
    deps = _load_dependencies()
    matches = [d for d in deps if d.startswith("pydantic")]
    assert matches, "pydantic must be declared in [project] dependencies"
