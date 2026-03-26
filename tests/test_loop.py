"""Tests for red_phase(), green_phase(), fix_loop(), and inner_loop() in wiggum.loop."""

import threading
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from wiggum.agent import AgentPort, AgentResult
from wiggum.config import WiggumConfig
from wiggum.git import GitPort
from wiggum.loop import (
    MAX_FIX_ATTEMPTS,
    CheckResult,
    find_gaps,
    fix_loop,
    green_phase,
    inner_loop,
    red_phase,
)
from wiggum.plan import PlanItem

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import pytest

    from wiggum.git.models import LogEntry, StatusEntry

_ITEMS: Sequence[PlanItem] = (
    PlanItem(description="Add user login endpoint"),
    PlanItem(description="Create database migration"),
    PlanItem(description="Write input validation"),
)


class FakeAgent:
    """Agent that records calls and returns canned results."""

    def __init__(self) -> None:
        self.run_calls: list[str] = []
        self._lock = threading.Lock()

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Record the prompt and return a successful result."""
        with self._lock:
            self.run_calls.append(prompt)
        return AgentResult(stdout="test written", stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


# -- Return shape --------------------------------------------------------------


class TestRedPhaseReturnShape:
    """Tests for the shape and type of red_phase return value."""

    def test_returns_list(self) -> None:
        agent = FakeAgent()
        result = red_phase(items=_ITEMS, agent=agent)
        assert isinstance(result, list)

    def test_elements_are_agent_results(self) -> None:
        agent = FakeAgent()
        result = red_phase(items=_ITEMS, agent=agent)
        assert all(isinstance(r, AgentResult) for r in result)

    def test_returns_one_result_per_item(self) -> None:
        agent = FakeAgent()
        result = red_phase(items=_ITEMS, agent=agent)
        assert len(result) == len(_ITEMS)


# -- Empty input ---------------------------------------------------------------


class TestRedPhaseEmptyInput:
    """Tests for red_phase with no items."""

    def test_empty_items_returns_empty_list(self) -> None:
        agent = FakeAgent()
        result = red_phase(items=[], agent=agent)
        assert result == []

    def test_empty_items_does_not_call_agent(self) -> None:
        agent = FakeAgent()
        red_phase(items=[], agent=agent)
        assert len(agent.run_calls) == 0


# -- Agent interaction ---------------------------------------------------------


class TestRedPhaseAgentInteraction:
    """Tests for how red_phase invokes the agent."""

    def test_calls_agent_once_per_item(self) -> None:
        agent = FakeAgent()
        red_phase(items=_ITEMS, agent=agent)
        assert len(agent.run_calls) == len(_ITEMS)

    def test_each_prompt_contains_item_description(self) -> None:
        agent = FakeAgent()
        red_phase(items=_ITEMS, agent=agent)
        for item in _ITEMS:
            assert any(item.description in prompt for prompt in agent.run_calls)


# -- Parallelism ---------------------------------------------------------------


class TestRedPhaseParallelism:
    """Tests that red_phase spawns agents in parallel."""

    def test_concurrent_execution(self) -> None:
        """Verify multiple agents run concurrently, not sequentially."""
        concurrency_high_water = 0
        active_count = 0
        lock = threading.Lock()

        class SlowAgent:
            """Agent that tracks concurrent execution."""

            run_calls: ClassVar[list[str]] = []

            def run(
                self,
                *,
                prompt: str,
                system_prompt: str | None = None,
                allowed_tools: Sequence[str] | None = None,
            ) -> AgentResult:
                """Track concurrent invocations."""
                nonlocal concurrency_high_water, active_count
                with lock:
                    active_count += 1
                    concurrency_high_water = max(concurrency_high_water, active_count)
                    self.run_calls.append(prompt)
                # yield to let other threads start
                threading.Event().wait(timeout=0.05)
                with lock:
                    active_count -= 1
                return AgentResult(stdout="test written", stderr="", exit_code=0)

            def run_background(self, *, prompt: str) -> object:
                """Not used."""
                raise NotImplementedError

        agent = SlowAgent()
        red_phase(items=_ITEMS, agent=agent)
        assert concurrency_high_water > 1


# -- Protocol conformance ------------------------------------------------------


class TestRedPhaseProtocol:
    """Tests that FakeAgent satisfies AgentPort protocol."""

    def test_fake_agent_is_agent_port(self) -> None:
        agent = FakeAgent()
        assert isinstance(agent, AgentPort)


# -- green_phase tests ---------------------------------------------------------

_GREEN_ITEMS: Sequence[PlanItem] = (
    PlanItem(description="Add database schema"),
    PlanItem(description="Write API endpoint"),
    PlanItem(description="Create frontend form"),
)


class _SequentialAgent:
    """Agent that records call order to verify sequential execution."""

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.call_order: list[int] = []
        self._counter = 0
        self._lock = threading.Lock()

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Record prompt and assign a sequential index."""
        with self._lock:
            self.prompts.append(prompt)
            self.call_order.append(self._counter)
            self._counter += 1
        return AgentResult(stdout="implemented", stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used by green_phase."""
        raise NotImplementedError


# -- Return shape --------------------------------------------------------------


class TestGreenPhaseReturnShape:
    """Tests for the shape and type of green_phase return value."""

    def test_returns_list(self) -> None:
        agent = _SequentialAgent()
        result = green_phase(items=_GREEN_ITEMS, agent=agent)
        assert isinstance(result, list)

    def test_elements_are_agent_results(self) -> None:
        agent = _SequentialAgent()
        result = green_phase(items=_GREEN_ITEMS, agent=agent)
        assert all(isinstance(r, AgentResult) for r in result)

    def test_returns_one_result_per_item(self) -> None:
        agent = _SequentialAgent()
        result = green_phase(items=_GREEN_ITEMS, agent=agent)
        assert len(result) == len(_GREEN_ITEMS)


# -- Empty input ---------------------------------------------------------------


class TestGreenPhaseEmptyInput:
    """Tests for green_phase with no items."""

    def test_empty_items_returns_empty_list(self) -> None:
        agent = _SequentialAgent()
        result = green_phase(items=[], agent=agent)
        assert result == []

    def test_empty_items_does_not_call_agent(self) -> None:
        agent = _SequentialAgent()
        green_phase(items=[], agent=agent)
        assert len(agent.prompts) == 0


# -- Agent interaction ---------------------------------------------------------


class TestGreenPhaseAgentInteraction:
    """Tests for how green_phase invokes the agent."""

    def test_calls_agent_once_per_item(self) -> None:
        agent = _SequentialAgent()
        green_phase(items=_GREEN_ITEMS, agent=agent)
        assert len(agent.prompts) == len(_GREEN_ITEMS)

    def test_each_prompt_contains_item_description(self) -> None:
        agent = _SequentialAgent()
        green_phase(items=_GREEN_ITEMS, agent=agent)
        for item, prompt in zip(_GREEN_ITEMS, agent.prompts, strict=True):
            assert item.description in prompt

    def test_single_item(self) -> None:
        single: Sequence[PlanItem] = (PlanItem(description="Solo task"),)
        agent = _SequentialAgent()
        result = green_phase(items=single, agent=agent)
        assert len(result) == 1
        assert len(agent.prompts) == 1
        assert "Solo task" in agent.prompts[0]


# -- Sequential execution -----------------------------------------------------


class TestGreenPhaseSequential:
    """Tests that green_phase runs agents sequentially, not in parallel."""

    def test_no_concurrent_execution(self) -> None:
        """Verify agents never run concurrently."""
        max_concurrent = 0
        active = 0
        lock = threading.Lock()

        class _ConcurrencyTracker:
            """Agent that detects concurrent invocations."""

            prompts: ClassVar[list[str]] = []

            def run(
                self,
                *,
                prompt: str,
                system_prompt: str | None = None,
                allowed_tools: Sequence[str] | None = None,
            ) -> AgentResult:
                """Track concurrent invocations via active counter."""
                nonlocal max_concurrent, active
                with lock:
                    active += 1
                    max_concurrent = max(max_concurrent, active)
                    self.prompts.append(prompt)
                threading.Event().wait(timeout=0.05)
                with lock:
                    active -= 1
                return AgentResult(stdout="done", stderr="", exit_code=0)

            def run_background(self, *, prompt: str) -> object:
                """Not used."""
                raise NotImplementedError

        agent = _ConcurrencyTracker()
        green_phase(items=_GREEN_ITEMS, agent=agent)
        assert max_concurrent == 1

    def test_calls_in_item_order(self) -> None:
        """Each call's prompt corresponds to the item at that index."""
        agent = _SequentialAgent()
        green_phase(items=_GREEN_ITEMS, agent=agent)
        for i, item in enumerate(_GREEN_ITEMS):
            assert item.description in agent.prompts[i]

    def test_results_match_item_order(self) -> None:
        """Results are returned in the same order as items."""
        results_per_item = [
            AgentResult(stdout=f"fix-{i}", stderr="", exit_code=0)
            for i in range(len(_GREEN_ITEMS))
        ]

        class _OrderedAgent:
            """Agent returning distinct results per call."""

            def __init__(self) -> None:
                self._index = 0

            def run(
                self,
                *,
                prompt: str,
                system_prompt: str | None = None,
                allowed_tools: Sequence[str] | None = None,
            ) -> AgentResult:
                """Return the next pre-configured result."""
                r = results_per_item[self._index]
                self._index += 1
                return r

            def run_background(self, *, prompt: str) -> object:
                """Not used."""
                raise NotImplementedError

        agent = _OrderedAgent()
        results = green_phase(items=_GREEN_ITEMS, agent=agent)
        for i, result in enumerate(results):
            assert result.stdout == f"fix-{i}"


# -- fix_loop helpers ----------------------------------------------------------


def _make_check(results: list[CheckResult]) -> Callable[[], CheckResult]:
    """Return a callable that yields successive check results."""
    it = iter(results)

    def check() -> CheckResult:
        return next(it)

    return check


# -- fix_loop: immediate pass --------------------------------------------------


class TestFixLoopImmediatePass:
    """fix_loop returns immediately when first check passes."""

    def test_returns_passing_result(self) -> None:
        """Passing initial check means no retry needed."""
        agent = FakeAgent()
        result = fix_loop(
            agent=agent,
            check=_make_check([CheckResult(passed=True, output="")]),
        )
        assert result.passed is True

    def test_does_not_invoke_agent(self) -> None:
        """Agent should not be called when checks already pass."""
        agent = FakeAgent()
        fix_loop(
            agent=agent,
            check=_make_check([CheckResult(passed=True, output="")]),
        )
        assert len(agent.run_calls) == 0


# -- fix_loop: retry behavior -------------------------------------------------


class TestFixLoopRetries:
    """fix_loop retries remediation up to MAX_FIX_ATTEMPTS on failure."""

    def test_calls_agent_on_check_failure(self) -> None:
        """A failing check triggers an agent remediation call."""
        results = [
            CheckResult(passed=False, output="error"),
            CheckResult(passed=True, output=""),
        ]
        agent = FakeAgent()
        fix_loop(agent=agent, check=_make_check(results))
        assert len(agent.run_calls) == 1

    def test_succeeds_on_second_attempt(self) -> None:
        """fix_loop returns success when remediation fixes the issue."""
        results = [
            CheckResult(passed=False, output="error"),
            CheckResult(passed=True, output=""),
        ]
        agent = FakeAgent()
        result = fix_loop(agent=agent, check=_make_check(results))
        assert result.passed is True

    def test_retries_up_to_max_attempts(self) -> None:
        """Agent is invoked exactly MAX_FIX_ATTEMPTS times before giving up."""
        results = [CheckResult(passed=False, output="error")] * (MAX_FIX_ATTEMPTS + 1)
        agent = FakeAgent()
        fix_loop(agent=agent, check=_make_check(results))
        assert len(agent.run_calls) == MAX_FIX_ATTEMPTS

    def test_returns_failure_after_max_retries(self) -> None:
        """fix_loop returns failure when all retry attempts are exhausted."""
        results = [CheckResult(passed=False, output="error")] * (MAX_FIX_ATTEMPTS + 1)
        agent = FakeAgent()
        result = fix_loop(agent=agent, check=_make_check(results))
        assert result.passed is False


# -- fix_loop: check invocation count -----------------------------------------


class TestFixLoopCheckCount:
    """fix_loop calls check the expected number of times."""

    def test_one_check_on_immediate_pass(self) -> None:
        """Only the initial check is called when it passes."""
        call_count = 0

        def counting_check() -> CheckResult:
            nonlocal call_count
            call_count += 1
            return CheckResult(passed=True, output="")

        fix_loop(agent=FakeAgent(), check=counting_check)
        assert call_count == 1

    def test_n_plus_one_checks_for_n_failures_then_pass(self) -> None:
        """Fail twice then pass: initial check + 2 retries = 3 check calls."""
        call_count = 0

        def counting_check() -> CheckResult:
            nonlocal call_count
            call_count += 1
            passed = call_count >= 3
            return CheckResult(passed=passed, output="" if passed else "error")

        fix_loop(agent=FakeAgent(), check=counting_check)
        assert call_count == 3

    def test_max_plus_one_checks_on_all_failures(self) -> None:
        """Initial check + MAX_FIX_ATTEMPTS retries = MAX_FIX_ATTEMPTS + 1 checks."""
        call_count = 0

        def counting_check() -> CheckResult:
            nonlocal call_count
            call_count += 1
            return CheckResult(passed=False, output="error")

        fix_loop(agent=FakeAgent(), check=counting_check)
        assert call_count == MAX_FIX_ATTEMPTS + 1


# -- fix_loop: agent receives check output ------------------------------------


class TestFixLoopAgentReceivesOutput:
    """fix_loop passes check output to the agent for remediation context."""

    def test_agent_prompt_contains_check_output(self) -> None:
        """The failing check output is included in the agent prompt."""
        error_output = "FAILED tests/test_foo.py::test_bar - AssertionError"
        results = [
            CheckResult(passed=False, output=error_output),
            CheckResult(passed=True, output=""),
        ]
        agent = FakeAgent()
        fix_loop(agent=agent, check=_make_check(results))
        assert error_output in agent.run_calls[0]


# -- fix_loop: constant value --------------------------------------------------


class TestMaxFixAttempts:
    """MAX_FIX_ATTEMPTS is the expected value."""

    def test_is_three(self) -> None:
        """The retry limit is 3."""
        assert MAX_FIX_ATTEMPTS == 3


# -- inner_loop fakes ---------------------------------------------------------

_ORCHESTRATION_PLAN = """\
# Test Plan

### Section A
- [ ] Add foo feature
- [ ] Add bar feature
- [x] Already done
"""

_ALL_CHECKED_PLAN = """\
# Test Plan

### Section A
- [x] Done one
- [x] Done two
"""


class _InnerLoopGit:
    """Git port that records stage and commit calls."""

    def __init__(self) -> None:
        self.commits: list[str] = []
        self.stage_all_count = 0
        self._call_log: list[str] = []

    def repo_root(self) -> Path:
        """Return a fake repo root."""
        return Path("/fake/repo")

    def is_repo(self) -> bool:
        """Return True."""
        return True

    def current_branch(self) -> str:
        """Return a fake branch name."""
        return "feat/test"

    def status(self) -> Sequence[StatusEntry]:
        """Return empty status."""
        return []

    def diff(self, *, staged: bool = False) -> str:
        """Return empty diff."""
        return ""

    def diff_names(self, *, staged: bool = False) -> Sequence[str]:
        """Return empty diff names."""
        return []

    def log(self, *, max_count: int = 10) -> Sequence[LogEntry]:
        """Return empty log."""
        return []

    def add(self, paths: Sequence[str]) -> None:
        """No-op."""

    def stage_all(self) -> None:
        """Record a stage_all call."""
        self._call_log.append("stage_all")
        self.stage_all_count += 1

    def commit(self, message: str) -> None:
        """Record a commit call."""
        self._call_log.append("commit")
        self.commits.append(message)

    def fetch(self, remote: str, branch: str) -> None:
        """No-op."""

    def rebase(self, onto: str) -> bool:
        """Return True (no conflict)."""
        return True

    def rebase_abort(self) -> None:
        """No-op."""

    def default_branch(self) -> str:
        """Return main."""
        return "main"


class _InnerLoopAgent:
    """Agent returning a numbered list for select_items and success for phases."""

    def __init__(self, item_descriptions: Sequence[str]) -> None:
        self.calls: list[str] = []
        self._response = "\n".join(
            f"{i + 1}. {d}" for i, d in enumerate(item_descriptions)
        )

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Record the call and return a canned numbered-list response."""
        self.calls.append(prompt)
        return AgentResult(stdout=self._response, stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


def _stub_fix_loop_pass(*_args: object, **_kwargs: object) -> CheckResult:
    """Stub fix_loop that always returns a passing result."""
    return CheckResult(passed=True, output="")


def _stub_fix_loop_fail(*_args: object, **_kwargs: object) -> CheckResult:
    """Stub fix_loop that always returns a failing result."""
    return CheckResult(passed=False, output="check failed")


# -- inner_loop: no work ------------------------------------------------------


class TestInnerLoopNoWork:
    """When all items are checked, inner_loop is a no-op."""

    def test_no_commit_when_all_checked(self, tmp_path: Path) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_ALL_CHECKED_PLAN)
        git = _InnerLoopGit()
        agent = _InnerLoopAgent([])
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=WiggumConfig())
        assert git.commits == []

    def test_no_agent_calls_when_all_checked(self, tmp_path: Path) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_ALL_CHECKED_PLAN)
        git = _InnerLoopGit()
        agent = _InnerLoopAgent([])
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=WiggumConfig())
        assert agent.calls == []


# -- inner_loop: orchestration -------------------------------------------------


class TestInnerLoopOrchestration:
    """inner_loop orchestrates select, red, green, check, mark, commit."""

    def test_marks_items_checked_in_plan_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_ORCHESTRATION_PLAN)
        git = _InnerLoopGit()
        agent = _InnerLoopAgent(["Add foo feature", "Add bar feature"])
        monkeypatch.setattr("wiggum.loop.fix_loop", _stub_fix_loop_pass)
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=WiggumConfig())
        content = plan_path.read_text()
        assert "- [x] Add foo feature" in content
        assert "- [x] Add bar feature" in content

    def test_previously_checked_items_remain_checked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_ORCHESTRATION_PLAN)
        git = _InnerLoopGit()
        agent = _InnerLoopAgent(["Add foo feature", "Add bar feature"])
        monkeypatch.setattr("wiggum.loop.fix_loop", _stub_fix_loop_pass)
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=WiggumConfig())
        content = plan_path.read_text()
        assert "- [x] Already done" in content

    def test_commits_after_marking(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_ORCHESTRATION_PLAN)
        git = _InnerLoopGit()
        agent = _InnerLoopAgent(["Add foo feature", "Add bar feature"])
        monkeypatch.setattr("wiggum.loop.fix_loop", _stub_fix_loop_pass)
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=WiggumConfig())
        assert len(git.commits) >= 1

    def test_stages_all_before_commit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_ORCHESTRATION_PLAN)
        git = _InnerLoopGit()
        agent = _InnerLoopAgent(["Add foo feature", "Add bar feature"])
        monkeypatch.setattr("wiggum.loop.fix_loop", _stub_fix_loop_pass)
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=WiggumConfig())
        assert git.stage_all_count >= 1
        stage_idx = git._call_log.index("stage_all")
        commit_idx = git._call_log.index("commit")
        assert stage_idx < commit_idx

    def test_invokes_agent_at_least_once(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_ORCHESTRATION_PLAN)
        git = _InnerLoopGit()
        agent = _InnerLoopAgent(["Add foo feature", "Add bar feature"])
        monkeypatch.setattr("wiggum.loop.fix_loop", _stub_fix_loop_pass)
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=WiggumConfig())
        assert len(agent.calls) >= 1


# -- inner_loop: check failure ------------------------------------------------


class TestInnerLoopCheckFailure:
    """When checks fail, items are not marked and no commit is made."""

    def test_no_mark_on_check_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_ORCHESTRATION_PLAN)
        git = _InnerLoopGit()
        agent = _InnerLoopAgent(["Add foo feature", "Add bar feature"])
        monkeypatch.setattr("wiggum.loop.fix_loop", _stub_fix_loop_fail)
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=WiggumConfig())
        content = plan_path.read_text()
        assert "- [ ] Add foo feature" in content
        assert "- [ ] Add bar feature" in content

    def test_no_commit_on_check_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_ORCHESTRATION_PLAN)
        git = _InnerLoopGit()
        agent = _InnerLoopAgent(["Add foo feature", "Add bar feature"])
        monkeypatch.setattr("wiggum.loop.fix_loop", _stub_fix_loop_fail)
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=WiggumConfig())
        assert git.commits == []


# -- inner_loop: batch size ----------------------------------------------------


class TestInnerLoopBatchSize:
    """inner_loop respects config.batch_size for item selection."""

    def test_processes_at_most_batch_size_items(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_text = "# Plan\n\n### Section\n"
        task_names = [f"Task {i}" for i in range(20)]
        for name in task_names:
            plan_text += f"- [ ] {name}\n"
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan_text)
        config = WiggumConfig(batch_size=3)
        agent = _InnerLoopAgent(task_names[:3])
        git = _InnerLoopGit()
        monkeypatch.setattr("wiggum.loop.fix_loop", _stub_fix_loop_pass)
        inner_loop(plan_path=plan_path, agent=agent, git=git, config=config)
        content = plan_path.read_text()
        checked_count = content.count("- [x]")
        assert checked_count <= 3


# -- inner_loop: protocol conformance -----------------------------------------


class TestInnerLoopProtocol:
    """Fakes satisfy their respective protocols."""

    def test_inner_loop_git_is_git_port(self) -> None:
        git = _InnerLoopGit()
        assert isinstance(git, GitPort)

    def test_inner_loop_agent_is_agent_port(self) -> None:
        agent = _InnerLoopAgent([])
        assert isinstance(agent, AgentPort)


# -- find_gaps fakes ----------------------------------------------------------

_GAPS_PLAN_TEXT = """\
# Test Plan

### Auth
- [x] Add login endpoint
- [ ] Add logout endpoint

### Database
- [x] Create users table
"""


class _GapsAgent:
    """Agent that returns a canned numbered list of gap descriptions."""

    def __init__(self, gaps: Sequence[str]) -> None:
        self.calls: list[str] = []
        self._response = "\n".join(f"{i + 1}. {g}" for i, g in enumerate(gaps))

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Record the call and return the canned response."""
        self.calls.append(prompt)
        return AgentResult(stdout=self._response, stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


# -- find_gaps: import --------------------------------------------------------


class TestFindGapsImport:
    """find_gaps is importable from wiggum.loop."""

    def test_importable(self) -> None:
        from wiggum.loop import find_gaps

        assert callable(find_gaps)


# -- find_gaps: return shape --------------------------------------------------


class TestFindGapsReturnShape:
    """find_gaps returns a list of strings."""

    def test_returns_list(self) -> None:
        agent = _GapsAgent(["Add password reset"])
        result = find_gaps(plan_text=_GAPS_PLAN_TEXT, agent=agent)
        assert isinstance(result, list)

    def test_elements_are_strings(self) -> None:
        agent = _GapsAgent(["Add password reset", "Add rate limiting"])
        result = find_gaps(plan_text=_GAPS_PLAN_TEXT, agent=agent)
        assert all(isinstance(item, str) for item in result)

    def test_returns_one_entry_per_gap(self) -> None:
        gaps = ["Add password reset", "Add rate limiting"]
        agent = _GapsAgent(gaps)
        result = find_gaps(plan_text=_GAPS_PLAN_TEXT, agent=agent)
        assert len(result) == len(gaps)


# -- find_gaps: agent interaction ----------------------------------------------


class TestFindGapsAgentInteraction:
    """find_gaps sends plan text to the agent."""

    def test_calls_agent_once(self) -> None:
        agent = _GapsAgent(["Add password reset"])
        find_gaps(plan_text=_GAPS_PLAN_TEXT, agent=agent)
        assert len(agent.calls) == 1

    def test_prompt_contains_plan_text(self) -> None:
        agent = _GapsAgent(["Add password reset"])
        find_gaps(plan_text=_GAPS_PLAN_TEXT, agent=agent)
        assert "Add login endpoint" in agent.calls[0]
        assert "Add logout endpoint" in agent.calls[0]
        assert "Create users table" in agent.calls[0]


# -- find_gaps: parsing -------------------------------------------------------


class TestFindGapsParsing:
    """find_gaps parses numbered items from agent output."""

    def test_parses_gap_descriptions(self) -> None:
        gaps = ["Add password reset", "Add rate limiting"]
        agent = _GapsAgent(gaps)
        result = find_gaps(plan_text=_GAPS_PLAN_TEXT, agent=agent)
        assert result == gaps

    def test_no_gaps_returns_empty_list(self) -> None:
        agent = _GapsAgent([])
        result = find_gaps(plan_text=_GAPS_PLAN_TEXT, agent=agent)
        assert result == []


# -- find_gaps: protocol conformance -------------------------------------------


class TestFindGapsProtocol:
    """_GapsAgent satisfies AgentPort protocol."""

    def test_gaps_agent_is_agent_port(self) -> None:
        agent = _GapsAgent([])
        assert isinstance(agent, AgentPort)


# -- red_phase prompt content --------------------------------------------------

_RED_BATCH: Sequence[PlanItem] = (
    PlanItem(description="Add user login endpoint"),
    PlanItem(description="Create database migration"),
    PlanItem(description="Write input validation"),
)

_RED_PLAN_TEXT = """\
# Phase 1

### Auth
- [x] Add session tokens
- [ ] Add user login endpoint

### DB
- [ ] Create database migration
"""


class _PromptCapturingAgent:
    """Agent that captures prompts for assertion."""

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self._lock = threading.Lock()

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Record the prompt."""
        with self._lock:
            self.prompts.append(prompt)
        return AgentResult(stdout="test written", stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


class TestRedPromptIncludesBatchList:
    """red_phase prompt includes descriptions of all items in the batch."""

    def test_prompt_contains_all_batch_descriptions(self) -> None:
        agent = _PromptCapturingAgent()
        single_item = [_RED_BATCH[0]]
        red_phase(
            items=single_item, agent=agent, batch=_RED_BATCH, plan_text=_RED_PLAN_TEXT
        )
        prompt = agent.prompts[0]
        for item in _RED_BATCH:
            assert item.description in prompt

    def test_batch_items_not_being_tested_still_appear(self) -> None:
        agent = _PromptCapturingAgent()
        single_item = [_RED_BATCH[0]]
        red_phase(
            items=single_item, agent=agent, batch=_RED_BATCH, plan_text=_RED_PLAN_TEXT
        )
        prompt = agent.prompts[0]
        assert _RED_BATCH[1].description in prompt
        assert _RED_BATCH[2].description in prompt


class TestRedPromptIncludesPlan:
    """red_phase prompt includes the existing plan text."""

    def test_prompt_contains_plan_text(self) -> None:
        agent = _PromptCapturingAgent()
        red_phase(
            items=list(_RED_BATCH[:1]),
            agent=agent,
            batch=_RED_BATCH,
            plan_text=_RED_PLAN_TEXT,
        )
        prompt = agent.prompts[0]
        assert "Add session tokens" in prompt
        assert "Create database migration" in prompt

    def test_plan_text_present_for_each_item(self) -> None:
        agent = _PromptCapturingAgent()
        red_phase(
            items=list(_RED_BATCH),
            agent=agent,
            batch=_RED_BATCH,
            plan_text=_RED_PLAN_TEXT,
        )
        for prompt in agent.prompts:
            assert "Phase 1" in prompt


class TestRedPromptIncludesPreamble:
    """red_phase prompt includes project conventions preamble."""

    def test_mentions_docstrings(self) -> None:
        agent = _PromptCapturingAgent()
        red_phase(
            items=list(_RED_BATCH[:1]),
            agent=agent,
            batch=_RED_BATCH,
            plan_text=_RED_PLAN_TEXT,
        )
        prompt = agent.prompts[0]
        assert "docstring" in prompt.lower()

    def test_mentions_type_checking(self) -> None:
        agent = _PromptCapturingAgent()
        red_phase(
            items=list(_RED_BATCH[:1]),
            agent=agent,
            batch=_RED_BATCH,
            plan_text=_RED_PLAN_TEXT,
        )
        prompt = agent.prompts[0]
        assert "TYPE_CHECKING" in prompt

    def test_mentions_pep695(self) -> None:
        agent = _PromptCapturingAgent()
        red_phase(
            items=list(_RED_BATCH[:1]),
            agent=agent,
            batch=_RED_BATCH,
            plan_text=_RED_PLAN_TEXT,
        )
        prompt = agent.prompts[0]
        assert "PEP 695" in prompt or "pep 695" in prompt.lower()

    def test_mentions_tc003_noqa(self) -> None:
        agent = _PromptCapturingAgent()
        red_phase(
            items=list(_RED_BATCH[:1]),
            agent=agent,
            batch=_RED_BATCH,
            plan_text=_RED_PLAN_TEXT,
        )
        prompt = agent.prompts[0]
        assert "TC003" in prompt


# -- extract_new_todos --------------------------------------------------------


class TestExtractNewTodosImport:
    """extract_new_todos is importable from wiggum.loop."""

    def test_importable(self) -> None:
        from wiggum.loop import extract_new_todos

        assert callable(extract_new_todos)


class TestExtractNewTodosParsing:
    """extract_new_todos parses NEW_TODO lines from agent output."""

    def test_extracts_single_todo(self) -> None:
        from wiggum.loop import extract_new_todos

        output = "some text\nNEW_TODO: Add input validation\nmore text"
        assert extract_new_todos(output) == ["Add input validation"]

    def test_extracts_multiple_todos(self) -> None:
        from wiggum.loop import extract_new_todos

        output = "NEW_TODO: First thing\nother stuff\nNEW_TODO: Second thing"
        assert extract_new_todos(output) == ["First thing", "Second thing"]

    def test_returns_empty_for_no_todos(self) -> None:
        from wiggum.loop import extract_new_todos

        assert extract_new_todos("all good, no issues") == []

    def test_returns_empty_for_empty_string(self) -> None:
        from wiggum.loop import extract_new_todos

        assert extract_new_todos("") == []

    def test_ignores_indented_lines(self) -> None:
        from wiggum.loop import extract_new_todos

        output = "  NEW_TODO: indented should be ignored"
        assert extract_new_todos(output) == []

    def test_ignores_mid_line_occurrences(self) -> None:
        from wiggum.loop import extract_new_todos

        output = "I found a NEW_TODO: that should be ignored"
        assert extract_new_todos(output) == []

    def test_preserves_order(self) -> None:
        from wiggum.loop import extract_new_todos

        output = "NEW_TODO: Alpha\nNEW_TODO: Beta\nNEW_TODO: Gamma"
        assert extract_new_todos(output) == ["Alpha", "Beta", "Gamma"]


# -- collect_scoped_todos -----------------------------------------------------


class TestCollectScopedTodosImport:
    """collect_scoped_todos is importable from wiggum.loop."""

    def test_importable(self) -> None:
        from wiggum.loop import collect_scoped_todos

        assert callable(collect_scoped_todos)


class TestCollectScopedTodosMapping:
    """collect_scoped_todos pairs NEW_TODOs with the items that produced them."""

    def test_maps_todos_to_producing_item(self) -> None:
        from wiggum.loop import collect_scoped_todos

        items = [
            PlanItem(description="Add login"),
            PlanItem(description="Add logout"),
        ]
        results = [
            AgentResult(
                stdout="NEW_TODO: Need auth middleware", stderr="", exit_code=0
            ),
            AgentResult(stdout="done, no gaps", stderr="", exit_code=0),
        ]
        scoped = collect_scoped_todos(items=items, results=results)
        assert scoped["Add login"] == ["Need auth middleware"]
        assert scoped["Add logout"] == []

    def test_multiple_todos_from_single_item(self) -> None:
        from wiggum.loop import collect_scoped_todos

        items = [PlanItem(description="Build API")]
        results = [
            AgentResult(
                stdout="NEW_TODO: Need schema\nNEW_TODO: Need validation",
                stderr="",
                exit_code=0,
            ),
        ]
        scoped = collect_scoped_todos(items=items, results=results)
        assert scoped["Build API"] == ["Need schema", "Need validation"]

    def test_no_todos_yields_empty_lists(self) -> None:
        from wiggum.loop import collect_scoped_todos

        items = [
            PlanItem(description="Task A"),
            PlanItem(description="Task B"),
        ]
        results = [
            AgentResult(stdout="done", stderr="", exit_code=0),
            AgentResult(stdout="done", stderr="", exit_code=0),
        ]
        scoped = collect_scoped_todos(items=items, results=results)
        assert scoped["Task A"] == []
        assert scoped["Task B"] == []

    def test_todos_are_not_merged_across_items(self) -> None:
        from wiggum.loop import collect_scoped_todos

        items = [
            PlanItem(description="Item X"),
            PlanItem(description="Item Y"),
        ]
        results = [
            AgentResult(stdout="NEW_TODO: Gap for X", stderr="", exit_code=0),
            AgentResult(stdout="NEW_TODO: Gap for Y", stderr="", exit_code=0),
        ]
        scoped = collect_scoped_todos(items=items, results=results)
        assert scoped["Item X"] == ["Gap for X"]
        assert scoped["Item Y"] == ["Gap for Y"]

    def test_empty_items_returns_empty_dict(self) -> None:
        from wiggum.loop import collect_scoped_todos

        scoped = collect_scoped_todos(items=[], results=[])
        assert scoped == {}


# -- Tool restriction tracking ------------------------------------------------


class _ToolTrackingAgent:
    """Agent that records allowed_tools passed to each call."""

    def __init__(self) -> None:
        self.run_kwargs: list[dict[str, object]] = []
        self._lock = threading.Lock()

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Record call kwargs including allowed_tools."""
        with self._lock:
            self.run_kwargs.append({"prompt": prompt, "allowed_tools": allowed_tools})
        return AgentResult(stdout="ok", stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


# -- red_phase: tool restrictions ---------------------------------------------


class TestRedPhaseToolRestrictions:
    """RED agents must not have Bash access."""

    def test_passes_allowed_tools(self) -> None:
        """red_phase must specify allowed_tools for each agent call."""
        agent = _ToolTrackingAgent()
        red_phase(items=list(_ITEMS), agent=agent)
        for call in agent.run_kwargs:
            assert call["allowed_tools"] is not None, (
                "red_phase must specify allowed_tools"
            )

    def test_excludes_bash(self) -> None:
        """RED agents must not have Bash in their allowed tools."""
        agent = _ToolTrackingAgent()
        red_phase(items=list(_ITEMS), agent=agent)
        for call in agent.run_kwargs:
            tools = call["allowed_tools"]
            assert tools is not None, "red_phase must specify allowed_tools"
            assert "Bash" not in tools


# -- green_phase: tool restrictions -------------------------------------------


class TestGreenPhaseToolRestrictions:
    """GREEN round 1 has no Bash (fast parallel)."""

    def test_passes_allowed_tools(self) -> None:
        """green_phase must specify allowed_tools for each agent call."""
        agent = _ToolTrackingAgent()
        green_phase(items=_GREEN_ITEMS, agent=agent)
        for call in agent.run_kwargs:
            assert call["allowed_tools"] is not None, (
                "green_phase must specify allowed_tools"
            )

    def test_excludes_bash(self) -> None:
        """GREEN round 1 agents must not have Bash in their allowed tools."""
        agent = _ToolTrackingAgent()
        green_phase(items=_GREEN_ITEMS, agent=agent)
        for call in agent.run_kwargs:
            tools = call["allowed_tools"]
            assert tools is not None, "green_phase must specify allowed_tools"
            assert "Bash" not in tools


# -- fix_loop: tool restrictions ----------------------------------------------


class TestFixLoopToolRestrictions:
    """GREEN fix rounds get Bash for ruff verification."""

    def test_passes_allowed_tools(self) -> None:
        """fix_loop must specify allowed_tools for each agent call."""
        agent = _ToolTrackingAgent()
        results = [
            CheckResult(passed=False, output="error"),
            CheckResult(passed=True, output=""),
        ]
        fix_loop(agent=agent, check=_make_check(results))
        for call in agent.run_kwargs:
            assert call["allowed_tools"] is not None, (
                "fix_loop must specify allowed_tools"
            )

    def test_includes_bash(self) -> None:
        """Fix round agents must have Bash in their allowed tools."""
        agent = _ToolTrackingAgent()
        results = [
            CheckResult(passed=False, output="error"),
            CheckResult(passed=True, output=""),
        ]
        fix_loop(agent=agent, check=_make_check(results))
        for call in agent.run_kwargs:
            tools = call["allowed_tools"]
            assert tools is not None, "fix_loop must specify allowed_tools"
            assert "Bash" in tools
