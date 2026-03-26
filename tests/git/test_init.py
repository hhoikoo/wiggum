"""Tests for wiggum.git package init."""

import importlib


def test_git_package_is_importable() -> None:
    """Importing wiggum.git should succeed."""
    mod = importlib.import_module("wiggum.git")
    assert mod.__name__ == "wiggum.git"


def test_git_port_exported_from_package() -> None:
    """GitPort should be importable from wiggum.git."""
    mod = importlib.import_module("wiggum.git")
    assert hasattr(mod, "GitPort")
