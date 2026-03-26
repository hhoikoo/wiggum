"""Tests for triage_failures() and fix_by_triage() grouping and fixing by root cause."""

import threading
from typing import TYPE_CHECKING

from wiggum.agent import AgentPort, AgentResult
from wiggum.loop import fix_by_triage, triage_failures

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


# =============================================================================
# fix_by_triage -- dispatches one fix agent per root cause group
# =============================================================================


class _TriageFixAgent:
    """Agent that handles triage (first call) and fix (subsequent calls)."""

    def __init__(self, groups: Sequence[str]) -> None:
        self.triage_calls: list[str] = []
        self.fix_calls: list[str] = []
        self._lock = threading.Lock()
        self._triage_response = "\n".join(f"{i + 1}. {g}" for i, g in enumerate(groups))
        self._call_count = 0

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Return triage response on first call, fix response on subsequent calls."""
        with self._lock:
            self._call_count += 1
            if self._call_count == 1:
                self.triage_calls.append(prompt)
                return AgentResult(stdout=self._triage_response, stderr="", exit_code=0)
            self.fix_calls.append(prompt)
            return AgentResult(stdout="fixed", stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


# -- importable ----------------------------------------------------------------


class TestFixByTriageImport:
    """fix_by_triage is importable from wiggum.loop."""

    def test_importable(self) -> None:
        assert callable(fix_by_triage)


# -- return shape --------------------------------------------------------------


class TestFixByTriageReturnShape:
    """fix_by_triage returns a list of AgentResult, one per root cause group."""

    def test_returns_list(self) -> None:
        groups = ["auth token missing", "db connection failure"]
        agent = _TriageFixAgent(groups)
        result = fix_by_triage(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert isinstance(result, list)

    def test_elements_are_agent_results(self) -> None:
        groups = ["auth token missing", "db connection failure"]
        agent = _TriageFixAgent(groups)
        result = fix_by_triage(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert all(isinstance(r, AgentResult) for r in result)

    def test_one_result_per_root_cause_group(self) -> None:
        groups = [
            "TypeError in auth: missing 'token' argument",
            "ConnectionError in db: cannot reach database",
            "ValueError in api: invalid schema version",
        ]
        agent = _TriageFixAgent(groups)
        result = fix_by_triage(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert len(result) == 3


# -- grouping reduces fix agents -----------------------------------------------


class TestFixByTriageGrouping:
    """fix_by_triage launches one fix agent per root cause, not per test failure."""

    def test_five_failures_two_causes_two_fix_calls(self) -> None:
        groups = [
            "TypeError in auth module: missing 'token' argument (test_login, test_logout)",
            "ConnectionError in db module: cannot reach database (test_connect, test_query)",
        ]
        agent = _TriageFixAgent(groups)
        fix_by_triage(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert len(agent.fix_calls) == 2

    def test_same_root_cause_produces_single_fix_call(self) -> None:
        groups = [
            "TypeError in auth module: missing 'token' argument (test_login, test_logout, test_refresh)",
        ]
        agent = _TriageFixAgent(groups)
        fix_by_triage(test_output=_SAME_ROOT_CAUSE, agent=agent)
        assert len(agent.fix_calls) == 1

    def test_three_distinct_causes_three_fix_calls(self) -> None:
        groups = [
            "TypeError in auth: missing 'token' argument",
            "ConnectionError in db: cannot reach database",
            "ValueError in api: invalid schema version",
        ]
        agent = _TriageFixAgent(groups)
        fix_by_triage(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert len(agent.fix_calls) == 3


# -- fix prompts contain root cause descriptions --------------------------------


class TestFixByTriagePromptContent:
    """Each fix agent receives the root cause description in its prompt."""

    def test_fix_prompt_contains_root_cause(self) -> None:
        groups = [
            "TypeError in auth: missing 'token' argument",
            "ConnectionError in db: cannot reach database",
        ]
        agent = _TriageFixAgent(groups)
        fix_by_triage(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert any("TypeError in auth" in p for p in agent.fix_calls)
        assert any("ConnectionError in db" in p for p in agent.fix_calls)

    def test_fix_prompt_does_not_contain_raw_test_output(self) -> None:
        groups = ["TypeError in auth: missing 'token' argument"]
        agent = _TriageFixAgent(groups)
        fix_by_triage(test_output=_SAME_ROOT_CAUSE, agent=agent)
        for prompt in agent.fix_calls:
            assert "FAILED tests/test_auth.py::test_login" not in prompt


# -- empty / no-op cases -------------------------------------------------------


class TestFixByTriageEmpty:
    """fix_by_triage with empty input or no root causes does not launch fix agents."""

    def test_empty_test_output_returns_empty(self) -> None:
        agent = _TriageFixAgent([])
        result = fix_by_triage(test_output="", agent=agent)
        assert result == []

    def test_empty_test_output_no_fix_calls(self) -> None:
        agent = _TriageFixAgent([])
        fix_by_triage(test_output="", agent=agent)
        assert len(agent.fix_calls) == 0

    def test_empty_test_output_no_triage_call(self) -> None:
        agent = _TriageFixAgent([])
        fix_by_triage(test_output="", agent=agent)
        assert len(agent.triage_calls) == 0


# -- triage is called first ----------------------------------------------------


class TestFixByTriageOrdering:
    """fix_by_triage calls triage before launching fix agents."""

    def test_triage_called_exactly_once(self) -> None:
        groups = ["auth token missing", "db connection failure"]
        agent = _TriageFixAgent(groups)
        fix_by_triage(test_output=_MULTIPLE_DISTINCT_FAILURES, agent=agent)
        assert len(agent.triage_calls) == 1
