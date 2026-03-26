"""Tests for triage_failures() grouping test failures by root cause."""

import threading
from typing import TYPE_CHECKING

from wiggum.agent import AgentPort, AgentResult
from wiggum.loop import triage_failures

if TYPE_CHECKING:
    from collections.abc import Sequence

_SINGLE_FAILURE = """\
FAILED tests/test_auth.py::test_login - TypeError: missing argument 'token'
"""

_MULTIPLE_DISTINCT_FAILURES = """\
FAILED tests/test_auth.py::test_login - TypeError: missing argument 'token'
FAILED tests/test_auth.py::test_logout - TypeError: missing argument 'token'
FAILED tests/test_db.py::test_connect - ConnectionError: cannot reach database
FAILED tests/test_db.py::test_query - ConnectionError: cannot reach database
FAILED tests/test_api.py::test_endpoint - ValueError: invalid schema version
"""

_SAME_ROOT_CAUSE = """\
FAILED tests/test_auth.py::test_login - TypeError: missing argument 'token'
FAILED tests/test_auth.py::test_logout - TypeError: missing argument 'token'
FAILED tests/test_auth.py::test_refresh - TypeError: missing argument 'token'
"""


class _TriageAgent:
    """Agent that returns a canned numbered list of root cause groups."""

    def __init__(self, groups: Sequence[str]) -> None:
        self.calls: list[str] = []
        self._lock = threading.Lock()
        self._response = "\n".join(f"{i + 1}. {g}" for i, g in enumerate(groups))

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Record the prompt and return the canned grouped response."""
        with self._lock:
            self.calls.append(prompt)
        return AgentResult(stdout=self._response, stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


# -- importable ----------------------------------------------------------------


class TestTriageImport:
    """triage_failures is importable from wiggum.loop."""

    def test_importable(self) -> None:
        assert callable(triage_failures)


# -- protocol conformance -----------------------------------------------------


class TestTriageProtocol:
    """_TriageAgent satisfies AgentPort."""

    def test_triage_agent_is_agent_port(self) -> None:
        agent = _TriageAgent([])
        assert isinstance(agent, AgentPort)


# -- return shape --------------------------------------------------------------


class TestTriageReturnShape:
    """triage_failures returns a list of strings."""

    def test_returns_list(self) -> None:
        agent = _TriageAgent(["auth token parameter missing"])
        result = triage_failures(test_output=_SINGLE_FAILURE, agent=agent)
        assert isinstance(result, list)

    def test_elements_are_strings(self) -> None:
        agent = _TriageAgent(["auth token issue", "db connection issue"])
        result = triage_failures(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert all(isinstance(item, str) for item in result)


# -- grouping behavior --------------------------------------------------------


class TestTriageGrouping:
    """triage_failures groups multiple failures by root cause."""

    def test_distinct_causes_produce_multiple_groups(self) -> None:
        groups = [
            "TypeError in auth module: missing 'token' argument (test_login, test_logout)",
            "ConnectionError in db module: cannot reach database (test_connect, test_query)",
            "ValueError in api module: invalid schema version (test_endpoint)",
        ]
        agent = _TriageAgent(groups)
        result = triage_failures(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert len(result) == 3

    def test_same_cause_produces_single_group(self) -> None:
        groups = [
            "TypeError in auth module: missing 'token' argument (test_login, test_logout, test_refresh)",
        ]
        agent = _TriageAgent(groups)
        result = triage_failures(test_output=_SAME_ROOT_CAUSE, agent=agent)
        assert len(result) == 1

    def test_group_descriptions_match_agent_output(self) -> None:
        groups = [
            "TypeError in auth: missing 'token' argument",
            "ConnectionError in db: cannot reach database",
        ]
        agent = _TriageAgent(groups)
        result = triage_failures(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert result == groups


# -- agent interaction ---------------------------------------------------------


class TestTriageAgentInteraction:
    """triage_failures sends test output to agent for analysis."""

    def test_calls_agent_once(self) -> None:
        agent = _TriageAgent(["some root cause"])
        triage_failures(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert len(agent.calls) == 1

    def test_prompt_contains_test_output(self) -> None:
        agent = _TriageAgent(["some root cause"])
        triage_failures(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert "TypeError: missing argument 'token'" in agent.calls[0]
        assert "ConnectionError: cannot reach database" in agent.calls[0]
        assert "ValueError: invalid schema version" in agent.calls[0]


# -- empty input ---------------------------------------------------------------


class TestTriageEmptyInput:
    """triage_failures with no failures returns an empty list."""

    def test_empty_output_returns_empty(self) -> None:
        agent = _TriageAgent([])
        result = triage_failures(test_output="", agent=agent)
        assert result == []

    def test_empty_output_does_not_call_agent(self) -> None:
        agent = _TriageAgent([])
        triage_failures(test_output="", agent=agent)
        assert len(agent.calls) == 0
