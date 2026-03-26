"""Inner-loop orchestration: red, green, check, fix, and commit."""

import dataclasses
import re
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from wiggum.checks import run_checks as _run_checks
from wiggum.plan import get_unchecked, mark_checked, parse_plan
from wiggum.priority import select_items

_NUMBERED_ITEM_RE = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)
_NEW_TODO_RE = re.compile(r"^NEW_TODO:\s+(.+)$", re.MULTILINE)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

    from wiggum.agent import AgentResult, AgentService
    from wiggum.config import WiggumConfig
    from wiggum.git import GitClient
    from wiggum.plan import PlanItem

MAX_FIX_ATTEMPTS = 3

_TOOLS_NO_BASH: tuple[str, ...] = ("Read", "Write", "Edit", "Glob", "Grep")
_TOOLS_WITH_BASH: tuple[str, ...] = (*_TOOLS_NO_BASH, "Bash")

_RED_PREAMBLE = """\
## Project Conventions

- All public classes, methods, and functions must have a one-line docstring.
- Imports used only in type annotations must be inside `if TYPE_CHECKING:` blocks.
- Use PEP 695 type parameters, not TypeVar.
- Add `# noqa: TC003` to runtime_checkable Protocol imports that must remain at runtime."""


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """Result of running project checks."""

    passed: bool
    output: str


def _build_red_prompt(
    *,
    item: PlanItem,
    batch: Sequence[PlanItem] | None = None,
    plan_text: str | None = None,
) -> str:
    """Build the full prompt for a single RED phase agent."""
    parts: list[str] = []
    if batch is not None or plan_text is not None:
        parts.append(_RED_PREAMBLE)
    if plan_text is not None:
        parts.append(f"## Existing Plan\n\n{plan_text}")
    if batch is not None:
        batch_list = "\n".join(f"- {b.description}" for b in batch)
        parts.append(f"## Current Batch\n\n{batch_list}")
    parts.append(f"Write a failing test for: {item.description}")
    return "\n\n".join(parts)


def red_phase(
    *,
    items: Sequence[PlanItem],
    agent: AgentService,
    batch: Sequence[PlanItem] | None = None,
    plan_text: str | None = None,
) -> list[AgentResult]:
    """Spawn parallel agents to write failing tests per item."""
    if not items:
        return []

    def _write_test(item: PlanItem) -> AgentResult:
        prompt = _build_red_prompt(item=item, batch=batch, plan_text=plan_text)
        return agent.run(prompt=prompt, allowed_tools=list(_TOOLS_NO_BASH))

    with ThreadPoolExecutor() as pool:
        return list(pool.map(_write_test, items))


def green_phase(*, items: Sequence[PlanItem], agent: AgentService) -> list[AgentResult]:
    """Spawn sequential agents to implement minimal fixes per item."""
    results: list[AgentResult] = []
    for item in items:
        result = agent.run(
            prompt=f"Implement the minimal fix for: {item.description}",
            allowed_tools=list(_TOOLS_NO_BASH),
        )
        results.append(result)
    return results


def fix_loop(*, agent: AgentService, check: Callable[[], CheckResult]) -> CheckResult:
    """Retry remediation up to MAX_FIX_ATTEMPTS on check failure."""
    result = check()
    for _ in range(MAX_FIX_ATTEMPTS):
        if result.passed:
            return result
        agent.run(
            prompt=f"Fix the following check failures:\n\n{result.output}",
            allowed_tools=list(_TOOLS_WITH_BASH),
        )
        result = check()
    return result


def triage_failures(*, test_output: str, agent: AgentService) -> list[str]:
    """Group test failures by root cause via agent analysis."""
    if not test_output.strip():
        return []
    result = agent.run(
        prompt=f"Group these test failures by root cause. Return a numbered list where each item describes one root cause and the affected tests:\n\n{test_output}",
    )
    return _NUMBERED_ITEM_RE.findall(result.stdout)


def fix_by_triage(*, test_output: str, agent: AgentService) -> list[AgentResult]:
    """Triage failures by root cause, then dispatch one fix agent per group."""
    if not test_output.strip():
        return []
    groups = triage_failures(test_output=test_output, agent=agent)
    if not groups:
        return []
    results: list[AgentResult] = []
    for group in groups:
        result = agent.run(
            prompt=f"Fix the root cause: {group}",
            allowed_tools=list(_TOOLS_WITH_BASH),
        )
        results.append(result)
    return results


def extract_new_todos(output: str) -> list[str]:
    """Parse NEW_TODO lines from agent output."""
    return _NEW_TODO_RE.findall(output)


def collect_scoped_todos(
    *,
    items: Sequence[PlanItem],
    results: Sequence[AgentResult],
) -> dict[str, list[str]]:
    """Pair NEW_TODOs with the plan items that produced them."""
    return {
        item.description: extract_new_todos(result.stdout)
        for item, result in zip(items, results, strict=True)
    }


def find_gaps(*, plan_text: str, agent: AgentService) -> list[str]:
    """Identify missing plan items via agent."""
    result = agent.run(
        prompt=f"Review this plan and list any missing items as a numbered list:\n\n{plan_text}",
    )
    return _NUMBERED_ITEM_RE.findall(result.stdout)


def inner_loop(
    *,
    plan_path: Path,
    agent: AgentService,
    git: GitClient,
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
