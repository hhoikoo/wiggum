"""Tests for verify_checked(), reorganize_findings(), outer_loop(), and rebase_onto_base() in wiggum.outer_loop."""

import json
import logging
import textwrap
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from wiggum.agent import AgentPort, AgentResult
from wiggum.config import WiggumConfig
from wiggum.outer_loop import (
    outer_loop,
    rebase_onto_base,
    reorganize_findings,
    verify_checked,
)
from wiggum.plan import PlanItem, parse_plan

if TYPE_CHECKING:
    from collections.abc import Sequence

    import pytest

    from wiggum.git.models import LogEntry, StatusEntry

PLAN_WITH_FINDINGS = textwrap.dedent("""\
    # Phase 1

    ### Dependencies & Build
    - [x] Set up project structure

    ### Git Package
    - [ ] Create GitPort protocol

    ### Additional Findings
    - [ ] Add pydantic to dependencies
    - [ ] Fix git adapter signature
""")

PLAN_WITHOUT_FINDINGS = textwrap.dedent("""\
    # Phase 1

    ### Dependencies & Build
    - [x] Set up project structure

    ### Git Package
    - [ ] Create GitPort protocol
""")

PLAN_WITH_EMPTY_FINDINGS = textwrap.dedent("""\
    # Phase 1

    ### Dependencies & Build
    - [x] Set up project structure

    ### Additional Findings
""")


class _FakeAgent:
    """Agent that returns a JSON mapping of findings to target sections."""

    def __init__(self, mapping: dict[str, str]) -> None:
        self.calls: list[str] = []
        self._mapping = mapping

    def run(self, *, prompt: str, system_prompt: str | None = None) -> AgentResult:
        """Return a JSON mapping response."""
        self.calls.append(prompt)
        return AgentResult(stdout=json.dumps(self._mapping), stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


# -- no-op cases --------------------------------------------------------------


class TestReorganizeFindingsNoOp:
    """reorganize_findings is a no-op when there are no findings to move."""

    def test_no_findings_section_returns_unchanged(self) -> None:
        agent = _FakeAgent({})
        result = reorganize_findings(text=PLAN_WITHOUT_FINDINGS, agent=agent)
        assert result == PLAN_WITHOUT_FINDINGS

    def test_no_findings_section_does_not_call_agent(self) -> None:
        agent = _FakeAgent({})
        reorganize_findings(text=PLAN_WITHOUT_FINDINGS, agent=agent)
        assert len(agent.calls) == 0

    def test_empty_findings_section_does_not_call_agent(self) -> None:
        agent = _FakeAgent({})
        reorganize_findings(text=PLAN_WITH_EMPTY_FINDINGS, agent=agent)
        assert len(agent.calls) == 0


# -- relocation ---------------------------------------------------------------


class TestReorganizeFindingsRelocation:
    """reorganize_findings moves items from Additional Findings to proper sections."""

    def test_items_appear_in_target_sections(self) -> None:
        mapping = {
            "Add pydantic to dependencies": "Dependencies & Build",
            "Fix git adapter signature": "Git Package",
        }
        agent = _FakeAgent(mapping)
        result = reorganize_findings(text=PLAN_WITH_FINDINGS, agent=agent)
        plan = parse_plan(result)
        deps = next(s for s in plan.sections if s.title == "Dependencies & Build")
        git = next(s for s in plan.sections if s.title == "Git Package")
        dep_descriptions = [i.description for i in deps.items]
        git_descriptions = [i.description for i in git.items]
        assert "Add pydantic to dependencies" in dep_descriptions
        assert "Fix git adapter signature" in git_descriptions

    def test_items_removed_from_findings_section(self) -> None:
        mapping = {
            "Add pydantic to dependencies": "Dependencies & Build",
            "Fix git adapter signature": "Git Package",
        }
        agent = _FakeAgent(mapping)
        result = reorganize_findings(text=PLAN_WITH_FINDINGS, agent=agent)
        plan = parse_plan(result)
        findings = [s for s in plan.sections if s.title == "Additional Findings"]
        if findings:
            assert all(i.description not in mapping for i in next(iter(findings)).items)

    def test_existing_items_in_target_section_preserved(self) -> None:
        mapping = {
            "Add pydantic to dependencies": "Dependencies & Build",
            "Fix git adapter signature": "Git Package",
        }
        agent = _FakeAgent(mapping)
        result = reorganize_findings(text=PLAN_WITH_FINDINGS, agent=agent)
        plan = parse_plan(result)
        deps = next(s for s in plan.sections if s.title == "Dependencies & Build")
        git = next(s for s in plan.sections if s.title == "Git Package")
        dep_descriptions = [i.description for i in deps.items]
        git_descriptions = [i.description for i in git.items]
        assert "Set up project structure" in dep_descriptions
        assert "Create GitPort protocol" in git_descriptions

    def test_relocated_items_are_unchecked(self) -> None:
        mapping = {"Add pydantic to dependencies": "Dependencies & Build"}
        agent = _FakeAgent(mapping)
        result = reorganize_findings(text=PLAN_WITH_FINDINGS, agent=agent)
        plan = parse_plan(result)
        deps = next(s for s in plan.sections if s.title == "Dependencies & Build")
        added = [
            i for i in deps.items if i.description == "Add pydantic to dependencies"
        ]
        assert len(added) == 1
        assert added[0].checked is False

    def test_preserves_plan_title(self) -> None:
        mapping = {"Add pydantic to dependencies": "Dependencies & Build"}
        agent = _FakeAgent(mapping)
        result = reorganize_findings(text=PLAN_WITH_FINDINGS, agent=agent)
        plan = parse_plan(result)
        assert plan.title == "Phase 1"


# -- agent interaction --------------------------------------------------------


class TestReorganizeFindingsAgentInteraction:
    """reorganize_findings calls the agent with findings and section context."""

    def test_calls_agent_exactly_once(self) -> None:
        mapping = {
            "Add pydantic to dependencies": "Dependencies & Build",
            "Fix git adapter signature": "Git Package",
        }
        agent = _FakeAgent(mapping)
        reorganize_findings(text=PLAN_WITH_FINDINGS, agent=agent)
        assert len(agent.calls) == 1

    def test_prompt_contains_finding_descriptions(self) -> None:
        mapping = {
            "Add pydantic to dependencies": "Dependencies & Build",
            "Fix git adapter signature": "Git Package",
        }
        agent = _FakeAgent(mapping)
        reorganize_findings(text=PLAN_WITH_FINDINGS, agent=agent)
        prompt = agent.calls[0]
        assert "Add pydantic to dependencies" in prompt
        assert "Fix git adapter signature" in prompt

    def test_prompt_contains_section_names(self) -> None:
        mapping = {
            "Add pydantic to dependencies": "Dependencies & Build",
            "Fix git adapter signature": "Git Package",
        }
        agent = _FakeAgent(mapping)
        reorganize_findings(text=PLAN_WITH_FINDINGS, agent=agent)
        prompt = agent.calls[0]
        assert "Dependencies & Build" in prompt
        assert "Git Package" in prompt


# -- return type ---------------------------------------------------------------


class TestReorganizeFindingsReturnType:
    """reorganize_findings returns a string."""

    def test_returns_string(self) -> None:
        mapping = {"Add pydantic to dependencies": "Dependencies & Build"}
        agent = _FakeAgent(mapping)
        result = reorganize_findings(text=PLAN_WITH_FINDINGS, agent=agent)
        assert isinstance(result, str)


# -- protocol conformance -----------------------------------------------------


class TestReorganizeFindingsProtocol:
    """Fake agent satisfies AgentPort protocol."""

    def test_fake_agent_is_agent_port(self) -> None:
        agent = _FakeAgent({})
        assert isinstance(agent, AgentPort)


# == verify_checked tests ====================================================

_MIXED_PLAN = parse_plan("""\
# Test Plan

### Section A
- [x] Add user login endpoint
- [ ] Create database migration
- [x] Write input validation
- [x] Set up CI pipeline
""")

_VC_ALL_UNCHECKED_PLAN = parse_plan("""\
# Test Plan

### Section A
- [ ] Add user login endpoint
- [ ] Create database migration
""")

_VC_ALL_CHECKED_PLAN = parse_plan("""\
# Test Plan

### Section A
- [x] Add user login endpoint
- [x] Write input validation
""")


class _VerifyAgent:
    """Agent that returns VERIFIED or UNVERIFIED based on configured items."""

    def __init__(self, *, unverified: set[str] | None = None) -> None:
        self.prompts: list[str] = []
        self._unverified = unverified or set()
        self._lock = threading.Lock()

    def run(self, *, prompt: str, system_prompt: str | None = None) -> AgentResult:
        """Return VERIFIED or UNVERIFIED based on item description."""
        with self._lock:
            self.prompts.append(prompt)
        for desc in self._unverified:
            if desc in prompt:
                return AgentResult(
                    stdout="UNVERIFIED: not found in codebase",
                    stderr="",
                    exit_code=0,
                )
        return AgentResult(
            stdout="VERIFIED: implementation found", stderr="", exit_code=0
        )

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


# -- no checked items --------------------------------------------------------


class TestVerifyCheckedNoCheckedItems:
    """When no items are checked, verify_checked has nothing to verify."""

    def test_returns_empty_for_all_unchecked(self) -> None:
        agent = _VerifyAgent()
        result = verify_checked(plan=_VC_ALL_UNCHECKED_PLAN, agent=agent)
        assert result == []

    def test_does_not_call_agent_for_unchecked(self) -> None:
        agent = _VerifyAgent()
        verify_checked(plan=_VC_ALL_UNCHECKED_PLAN, agent=agent)
        assert len(agent.prompts) == 0


# -- all verified ------------------------------------------------------------


class TestVerifyCheckedAllVerified:
    """When all checked items are verified, returns empty list."""

    def test_returns_empty_when_all_verified(self) -> None:
        agent = _VerifyAgent()
        result = verify_checked(plan=_VC_ALL_CHECKED_PLAN, agent=agent)
        assert result == []


# -- some unverified ---------------------------------------------------------


class TestVerifyCheckedSomeUnverified:
    """When some checked items fail verification, those items are returned."""

    def test_returns_single_unverified_item(self) -> None:
        agent = _VerifyAgent(unverified={"Write input validation"})
        result = verify_checked(plan=_MIXED_PLAN, agent=agent)
        assert len(result) == 1
        assert result[0].description == "Write input validation"

    def test_returns_multiple_unverified_items(self) -> None:
        agent = _VerifyAgent(
            unverified={"Add user login endpoint", "Set up CI pipeline"}
        )
        result = verify_checked(plan=_MIXED_PLAN, agent=agent)
        descriptions = {item.description for item in result}
        assert descriptions == {"Add user login endpoint", "Set up CI pipeline"}

    def test_all_checked_items_unverified(self) -> None:
        agent = _VerifyAgent(
            unverified={"Add user login endpoint", "Write input validation"}
        )
        result = verify_checked(plan=_VC_ALL_CHECKED_PLAN, agent=agent)
        assert len(result) == 2


# -- agent interaction -------------------------------------------------------


class TestVerifyCheckedAgentInteraction:
    """verify_checked calls agent once per checked item."""

    def test_calls_agent_once_per_checked_item(self) -> None:
        agent = _VerifyAgent()
        verify_checked(plan=_MIXED_PLAN, agent=agent)
        assert len(agent.prompts) == 3

    def test_prompt_contains_item_description(self) -> None:
        agent = _VerifyAgent()
        verify_checked(plan=_MIXED_PLAN, agent=agent)
        checked_descriptions = {
            "Add user login endpoint",
            "Write input validation",
            "Set up CI pipeline",
        }
        for desc in checked_descriptions:
            assert any(desc in prompt for prompt in agent.prompts)

    def test_unchecked_items_not_sent_to_agent(self) -> None:
        agent = _VerifyAgent()
        verify_checked(plan=_MIXED_PLAN, agent=agent)
        assert not any("Create database migration" in p for p in agent.prompts)


# -- return type -------------------------------------------------------------


class TestVerifyCheckedReturnType:
    """verify_checked returns a list of PlanItem."""

    def test_returns_list(self) -> None:
        agent = _VerifyAgent()
        result = verify_checked(plan=_MIXED_PLAN, agent=agent)
        assert isinstance(result, list)

    def test_elements_are_plan_items(self) -> None:
        agent = _VerifyAgent(unverified={"Write input validation"})
        result = verify_checked(plan=_MIXED_PLAN, agent=agent)
        assert all(isinstance(item, PlanItem) for item in result)

    def test_returned_items_are_checked(self) -> None:
        agent = _VerifyAgent(unverified={"Write input validation"})
        result = verify_checked(plan=_MIXED_PLAN, agent=agent)
        assert all(item.checked for item in result)


# -- protocol conformance ----------------------------------------------------


class TestVerifyCheckedProtocol:
    """Fake agent satisfies AgentPort protocol."""

    def test_verify_agent_is_agent_port(self) -> None:
        agent = _VerifyAgent()
        assert isinstance(agent, AgentPort)


# == outer_loop tests ========================================================

_OL_PLAN_WITH_WORK = """\
# Test Plan

### Section A
- [ ] Build widget
- [ ] Test widget
- [x] Setup project
"""

_OL_FULLY_CHECKED = """\
# Test Plan

### Section A
- [x] Done one
- [x] Done two
"""


class _OuterLoopGit:
    """Minimal git port for outer_loop tests."""

    def repo_root(self) -> Path:
        """Return a fake repo root."""
        return Path("/fake")

    def is_repo(self) -> bool:
        """Return True."""
        return True

    def current_branch(self) -> str:
        """Return a fake branch."""
        return "main"

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
        """No-op."""

    def commit(self, message: str) -> None:
        """No-op."""

    def fetch(self, remote: str, branch: str) -> None:
        """No-op."""

    def rebase(self, onto: str) -> bool:
        """Return True (success)."""
        return True

    def rebase_continue(self) -> bool:
        """Return True (success)."""
        return True

    def rebase_abort(self) -> None:
        """No-op."""

    def default_branch(self) -> str:
        """Return main."""
        return "main"


class _OuterLoopAgent:
    """Minimal agent port for outer_loop tests."""

    def run(self, *, prompt: str, system_prompt: str | None = None) -> AgentResult:
        """Return a successful result."""
        return AgentResult(stdout="ok", stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


def _patch_outer_deps(
    monkeypatch: pytest.MonkeyPatch,
    call_log: list[str],
    plan_path: Path,
    *,
    items_per_cycle: int = 0,
) -> None:
    """Patch verify_checked, find_gaps, reorganize_findings, and inner_loop for outer_loop tests."""

    def _verify(**_kw: object) -> None:
        call_log.append("verify_checked")

    def _gaps(**_kw: object) -> None:
        call_log.append("find_gaps")

    def _reorg(**_kw: object) -> None:
        call_log.append("reorganize_findings")

    def _inner(**_kw: object) -> None:
        call_log.append("inner_loop")
        if items_per_cycle > 0:
            text = plan_path.read_text()
            for _ in range(items_per_cycle):
                text = text.replace("- [ ]", "- [x]", 1)
            plan_path.write_text(text)

    monkeypatch.setattr("wiggum.outer_loop.verify_checked", _verify)
    monkeypatch.setattr("wiggum.outer_loop.find_gaps", _gaps)
    monkeypatch.setattr("wiggum.outer_loop.reorganize_findings", _reorg)
    monkeypatch.setattr("wiggum.outer_loop.inner_loop", _inner)


# -- call order ---------------------------------------------------------------


class TestOuterLoopCallOrder:
    """outer_loop calls verify, gaps, reorganize before inner_loop."""

    def test_verify_before_first_inner_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_PLAN_WITH_WORK)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path, items_per_cycle=2)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(),
        )

        assert "verify_checked" in call_log
        assert "inner_loop" in call_log
        assert call_log.index("verify_checked") < call_log.index("inner_loop")

    def test_find_gaps_before_first_inner_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_PLAN_WITH_WORK)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path, items_per_cycle=2)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(),
        )

        assert "find_gaps" in call_log
        assert call_log.index("find_gaps") < call_log.index("inner_loop")

    def test_reorganize_before_first_inner_loop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_PLAN_WITH_WORK)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path, items_per_cycle=2)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(),
        )

        assert "reorganize_findings" in call_log
        assert call_log.index("reorganize_findings") < call_log.index("inner_loop")

    def test_order_is_verify_gaps_reorganize_then_inner(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_PLAN_WITH_WORK)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path, items_per_cycle=2)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(),
        )

        assert call_log[:4] == [
            "verify_checked",
            "find_gaps",
            "reorganize_findings",
            "inner_loop",
        ]


# -- no work ------------------------------------------------------------------


class TestOuterLoopNoWork:
    """When plan is fully checked, inner_loop is never called."""

    def test_no_inner_loop_when_fully_checked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_FULLY_CHECKED)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(),
        )

        assert "inner_loop" not in call_log

    def test_still_runs_verify_when_fully_checked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_FULLY_CHECKED)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(),
        )

        assert "verify_checked" in call_log

    def test_still_runs_find_gaps_when_fully_checked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_FULLY_CHECKED)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(),
        )

        assert "find_gaps" in call_log


# -- termination --------------------------------------------------------------


class TestOuterLoopTermination:
    """outer_loop stops when no unchecked items remain."""

    def test_inner_loop_called_once_per_batch_needed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_PLAN_WITH_WORK)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path, items_per_cycle=1)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(),
        )

        assert call_log.count("inner_loop") == 2

    def test_single_cycle_when_all_items_done_in_one_batch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_PLAN_WITH_WORK)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path, items_per_cycle=2)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(),
        )

        assert call_log.count("inner_loop") == 1


# -- cycle limit --------------------------------------------------------------


class TestOuterLoopCycleLimit:
    """outer_loop respects config.cycle_limit."""

    def test_stops_at_cycle_limit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_text = "# Plan\n\n### Section\n"
        for i in range(10):
            plan_text += f"- [ ] Task {i}\n"
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan_text)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path, items_per_cycle=1)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(cycle_limit=3),
        )

        assert call_log.count("inner_loop") == 3

    def test_zero_cycle_limit_runs_until_done(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_PLAN_WITH_WORK)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path, items_per_cycle=1)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(cycle_limit=0),
        )

        assert call_log.count("inner_loop") == 2

    def test_cycle_limit_one_runs_single_batch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(_OL_PLAN_WITH_WORK)
        call_log: list[str] = []
        _patch_outer_deps(monkeypatch, call_log, plan_path, items_per_cycle=1)

        outer_loop(
            plan_path=plan_path,
            agent=_OuterLoopAgent(),
            git=_OuterLoopGit(),
            config=WiggumConfig(cycle_limit=1),
        )

        assert call_log.count("inner_loop") == 1


# -- protocol conformance for outer_loop fakes --------------------------------


class TestOuterLoopProtocol:
    """Fakes satisfy their respective protocols."""

    def test_outer_loop_git_is_git_port(self) -> None:
        from wiggum.git import GitPort

        assert isinstance(_OuterLoopGit(), GitPort)

    def test_outer_loop_agent_is_agent_port(self) -> None:
        assert isinstance(_OuterLoopAgent(), AgentPort)


# == rebase_onto_base tests ==================================================


class _RebaseGit:
    """Git fake that records calls for rebase_onto_base tests."""

    def __init__(self, *, rebase_succeeds: bool = True, default: str = "main") -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self._rebase_succeeds = rebase_succeeds
        self._default = default

    def repo_root(self) -> Path:
        """Return a fake repo root."""
        return Path("/fake")

    def is_repo(self) -> bool:
        """Return True."""
        return True

    def current_branch(self) -> str:
        """Return a fake branch."""
        return "feat/work"

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
        """No-op."""

    def commit(self, message: str) -> None:
        """No-op."""

    def fetch(self, remote: str, branch: str) -> None:
        """Record fetch call."""
        self.calls.append(("fetch", (remote, branch)))

    def rebase(self, onto: str) -> bool:
        """Record rebase call and return configured result."""
        self.calls.append(("rebase", (onto,)))
        return self._rebase_succeeds

    def rebase_continue(self) -> bool:
        """Record rebase_continue call."""
        self.calls.append(("rebase_continue", ()))
        return True

    def rebase_abort(self) -> None:
        """Record rebase_abort call."""
        self.calls.append(("rebase_abort", ()))

    def default_branch(self) -> str:
        """Return configured default branch."""
        self.calls.append(("default_branch", ()))
        return self._default


# -- base branch selection ----------------------------------------------------


class TestRebaseOntoBaseBranchSelection:
    """rebase_onto_base uses config.base_branch when set, otherwise auto-detects."""

    def test_uses_config_base_branch(self) -> None:
        git = _RebaseGit()
        config = WiggumConfig(base_branch="develop")
        rebase_onto_base(git=git, config=config)
        fetch_calls = [c for c in git.calls if c[0] == "fetch"]
        assert len(fetch_calls) == 1
        assert fetch_calls[0][1] == ("origin", "develop")

    def test_auto_detects_when_base_branch_is_none(self) -> None:
        git = _RebaseGit(default="trunk")
        config = WiggumConfig(base_branch=None)
        rebase_onto_base(git=git, config=config)
        assert ("default_branch", ()) in git.calls

    def test_fetches_auto_detected_branch(self) -> None:
        git = _RebaseGit(default="trunk")
        config = WiggumConfig(base_branch=None)
        rebase_onto_base(git=git, config=config)
        fetch_calls = [c for c in git.calls if c[0] == "fetch"]
        assert len(fetch_calls) == 1
        assert fetch_calls[0][1] == ("origin", "trunk")


# -- fetch and rebase --------------------------------------------------------


class TestRebaseOntoBaseFetchAndRebase:
    """rebase_onto_base fetches then rebases onto the remote base branch."""

    def test_rebases_onto_remote_ref(self) -> None:
        git = _RebaseGit()
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config)
        rebase_calls = [c for c in git.calls if c[0] == "rebase"]
        assert len(rebase_calls) == 1
        assert rebase_calls[0][1] == ("origin/main",)

    def test_fetch_before_rebase(self) -> None:
        git = _RebaseGit()
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config)
        call_names = [c[0] for c in git.calls]
        assert call_names.index("fetch") < call_names.index("rebase")


# -- conflict handling -------------------------------------------------------


class TestRebaseOntoBaseConflict:
    """rebase_onto_base aborts rebase on conflict."""

    def test_aborts_on_conflict(self) -> None:
        git = _RebaseGit(rebase_succeeds=False)
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config)
        assert ("rebase_abort", ()) in git.calls

    def test_no_abort_on_success(self) -> None:
        git = _RebaseGit(rebase_succeeds=True)
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config)
        abort_calls = [c for c in git.calls if c[0] == "rebase_abort"]
        assert len(abort_calls) == 0


# -- protocol conformance for rebase git fake ---------------------------------


class TestRebaseOntoBaseProtocol:
    """Rebase git fake satisfies GitClient protocol."""

    def test_rebase_git_is_git_port(self) -> None:
        from wiggum.git import GitPort

        assert isinstance(_RebaseGit(), GitPort)


# == rebase conflict resolution tests ========================================


class _ConflictRebaseGit:
    """Git fake that returns configurable results on successive rebase calls."""

    def __init__(
        self,
        *,
        rebase_results: list[bool],
        continue_result: bool = True,
        default: str = "main",
    ) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self._rebase_results = list(rebase_results)
        self._rebase_index = 0
        self._continue_result = continue_result
        self._default = default

    def repo_root(self) -> Path:
        """Return a fake repo root."""
        return Path("/fake")

    def is_repo(self) -> bool:
        """Return True."""
        return True

    def current_branch(self) -> str:
        """Return a fake branch."""
        return "feat/work"

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
        """No-op."""

    def commit(self, message: str) -> None:
        """No-op."""

    def fetch(self, remote: str, branch: str) -> None:
        """Record fetch call."""
        self.calls.append(("fetch", (remote, branch)))

    def rebase(self, onto: str) -> bool:
        """Record rebase call, returning the next configured result."""
        self.calls.append(("rebase", (onto,)))
        result = self._rebase_results[self._rebase_index]
        self._rebase_index = min(self._rebase_index + 1, len(self._rebase_results) - 1)
        return result

    def rebase_continue(self) -> bool:
        """Record rebase_continue call and return configured result."""
        self.calls.append(("rebase_continue", ()))
        return self._continue_result

    def rebase_abort(self) -> None:
        """Record rebase_abort call."""
        self.calls.append(("rebase_abort", ()))

    def default_branch(self) -> str:
        """Return configured default branch."""
        self.calls.append(("default_branch", ()))
        return self._default


class _ConflictAgent:
    """Agent that records calls for conflict-resolution tests."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Record the call and return success."""
        self.calls.append(prompt)
        return AgentResult(stdout="resolved", stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used."""
        raise NotImplementedError


# -- agent invocation on conflict --------------------------------------------


class TestRebaseConflictInvokesAgent:
    """On first rebase conflict, agent is invoked for conflict resolution."""

    def test_agent_called_on_conflict(self) -> None:
        git = _ConflictRebaseGit(rebase_results=[False, True])
        agent = _ConflictAgent()
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config, agent=agent)
        assert len(agent.calls) == 1

    def test_agent_not_called_on_success(self) -> None:
        git = _ConflictRebaseGit(rebase_results=[True])
        agent = _ConflictAgent()
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config, agent=agent)
        assert len(agent.calls) == 0


# -- retry after agent resolution -------------------------------------------


class TestRebaseConflictRetry:
    """After agent resolves conflicts, rebase_continue is called."""

    def test_rebase_continue_called_after_conflict(self) -> None:
        git = _ConflictRebaseGit(rebase_results=[False], continue_result=True)
        agent = _ConflictAgent()
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config, agent=agent)
        continue_calls = [c for c in git.calls if c[0] == "rebase_continue"]
        assert len(continue_calls) == 1

    def test_no_abort_when_continue_succeeds(self) -> None:
        git = _ConflictRebaseGit(rebase_results=[False], continue_result=True)
        agent = _ConflictAgent()
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config, agent=agent)
        abort_calls = [c for c in git.calls if c[0] == "rebase_abort"]
        assert len(abort_calls) == 0


# -- abort when retry also fails ---------------------------------------------


class TestRebaseConflictRetryFails:
    """When rebase_continue also fails, rebase is aborted and function continues."""

    def test_abort_on_continue_failure(self) -> None:
        git = _ConflictRebaseGit(rebase_results=[False], continue_result=False)
        agent = _ConflictAgent()
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config, agent=agent)
        assert ("rebase_abort", ()) in git.calls

    def test_does_not_raise_on_continue_failure(self) -> None:
        git = _ConflictRebaseGit(rebase_results=[False], continue_result=False)
        agent = _ConflictAgent()
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config, agent=agent)

    def test_warning_logged_on_continue_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        git = _ConflictRebaseGit(rebase_results=[False], continue_result=False)
        agent = _ConflictAgent()
        config = WiggumConfig(base_branch="main")
        with caplog.at_level(logging.WARNING, logger="wiggum.outer_loop"):
            rebase_onto_base(git=git, config=config, agent=agent)
        assert any("rebase" in r.message.lower() for r in caplog.records)


# -- call order during conflict resolution -----------------------------------


class TestRebaseConflictCallOrder:
    """Agent is called between rebase and rebase_continue."""

    def test_agent_called_after_rebase_before_continue(self) -> None:
        git = _ConflictRebaseGit(rebase_results=[False], continue_result=True)
        agent = _ConflictAgent()
        config = WiggumConfig(base_branch="main")
        rebase_onto_base(git=git, config=config, agent=agent)
        call_names = [c[0] for c in git.calls]
        rebase_idx = call_names.index("rebase")
        continue_idx = call_names.index("rebase_continue")
        assert rebase_idx < continue_idx
        assert len(agent.calls) == 1


# -- protocol conformance for conflict fakes ---------------------------------


class TestRebaseConflictProtocol:
    """Conflict-resolution fakes satisfy their respective protocols."""

    def test_conflict_rebase_git_is_git_port(self) -> None:
        from wiggum.git import GitPort

        assert isinstance(_ConflictRebaseGit(rebase_results=[True]), GitPort)

    def test_conflict_agent_is_agent_port(self) -> None:
        assert isinstance(_ConflictAgent(), AgentPort)
