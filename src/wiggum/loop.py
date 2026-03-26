"""Inner-loop orchestration: red, green, check, fix, and commit."""

import dataclasses
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from wiggum.checks import run_checks as _run_checks
from wiggum.plan import get_unchecked, mark_checked, parse_plan
from wiggum.priority import select_items

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from wiggum.agent import AgentPort, AgentResult
    from wiggum.config import WiggumConfig
    from wiggum.git import GitPort
    from wiggum.plan import PlanItem

MAX_FIX_ATTEMPTS = 3


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """Result of running project checks."""

    passed: bool
    output: str


def red_phase(*, items: Sequence[PlanItem], agent: AgentPort) -> list[AgentResult]:
    """Spawn parallel agents to write failing tests per item."""
    if not items:
        return []

    def _write_test(item: PlanItem) -> AgentResult:
        return agent.run(prompt=f"Write a failing test for: {item.description}")

    with ThreadPoolExecutor() as pool:
        return list(pool.map(_write_test, items))


def green_phase(*, items: Sequence[PlanItem], agent: AgentPort) -> list[AgentResult]:
    """Spawn sequential agents to implement minimal fixes per item."""
    results: list[AgentResult] = []
    for item in items:
        result = agent.run(prompt=f"Implement the minimal fix for: {item.description}")
        results.append(result)
    return results


def fix_loop(*, agent: AgentPort, check: Callable[[], CheckResult]) -> CheckResult:
    """Retry remediation up to MAX_FIX_ATTEMPTS on check failure."""
    result = check()
    for _ in range(MAX_FIX_ATTEMPTS):
        if result.passed:
            return result
        agent.run(prompt=f"Fix the following check failures:\n\n{result.output}")
        result = check()
    return result


def inner_loop(
    *,
    plan_path: Path,
    agent: AgentPort,
    git: GitPort,
    config: WiggumConfig,
) -> None:
    """Orchestrate select, red, green, check, mark, and commit."""
    plan = parse_plan(plan_path.read_text())
    unchecked = get_unchecked(plan)
    if not unchecked:
        return

    selected = select_items(items=unchecked, agent=agent, count=config.batch_size)
    if not selected:
        return

    red_phase(items=selected, agent=agent)
    green_phase(items=selected, agent=agent)

    def _check() -> CheckResult:
        raw = _run_checks(repo_path=git.repo_root())
        parts: list[str] = []
        if not raw.lint_passed:
            parts.append(raw.lint_output)
        if not raw.test_passed:
            parts.append(raw.test_output)
        return CheckResult(passed=raw.passed, output="\n".join(parts))

    result = fix_loop(agent=agent, check=_check)
    if not result.passed:
        return

    text = plan_path.read_text()
    for item in selected:
        text = mark_checked(text, item.description)
    plan_path.write_text(text)

    git.stage_all()
    descriptions = ", ".join(item.description for item in selected)
    git.commit(f"feat: implement {descriptions}")
