"""Tests for wiggum.agent package init."""

import dataclasses
import importlib

from wiggum.agent import AgentPort, AgentResult


def test_agent_package_is_importable() -> None:
    """Importing wiggum.agent should succeed."""
    mod = importlib.import_module("wiggum.agent")
    assert mod is not None


def test_agent_package_has_dunder_path() -> None:
    """wiggum.agent should be a package (has __path__)."""
    mod = importlib.import_module("wiggum.agent")
    assert hasattr(mod, "__path__")


# -- AgentResult dataclass ---------------------------------------------------


def test_agent_result_is_dataclass():
    assert dataclasses.is_dataclass(AgentResult)


def test_agent_result_fields():
    result = AgentResult(stdout="hello", stderr="", exit_code=0)
    assert result.stdout == "hello"
    assert result.stderr == ""
    assert result.exit_code == 0


def test_agent_result_output_aliases_stdout():
    result = AgentResult(stdout="output text", stderr="", exit_code=0)
    assert result.output == "output text"


def test_agent_result_output_reflects_stdout_value():
    r1 = AgentResult(stdout="aaa", stderr="err", exit_code=1)
    r2 = AgentResult(stdout="bbb", stderr="", exit_code=0)
    assert r1.output == "aaa"
    assert r2.output == "bbb"


def test_agent_result_nonzero_exit_code():
    result = AgentResult(stdout="", stderr="fail", exit_code=1)
    assert result.exit_code == 1
    assert result.stderr == "fail"


# -- AgentPort protocol ------------------------------------------------------


def test_agent_port_is_protocol():
    assert hasattr(AgentPort, "__protocol_attrs__") or hasattr(
        AgentPort, "_is_protocol"
    )
    assert hasattr(AgentPort, "run")
    assert hasattr(AgentPort, "run_background")
