"""Outer-loop orchestration: verify, gaps, reorganize, and inner_loop batches."""

import json
import logging
from typing import TYPE_CHECKING

from wiggum.loop import inner_loop
from wiggum.plan import Plan, PlanItem, append_todo, count_unchecked, parse_plan

if TYPE_CHECKING:
    from pathlib import Path

    from wiggum.agent import AgentService
    from wiggum.config import WiggumConfig
    from wiggum.git import GitClient

_log = logging.getLogger(__name__)


def rebase_onto_base(
    *,
    git: GitClient,
    config: WiggumConfig,
    agent: AgentService | None = None,
) -> None:
    """Fetch and rebase working branch onto the base branch."""
    branch = (
        config.base_branch if config.base_branch is not None else git.default_branch()
    )
    git.fetch("origin", branch)
    if git.rebase(f"origin/{branch}"):
        return
    if agent is not None:
        agent.run(prompt="Resolve the current rebase conflicts in the working tree.")
        if git.rebase_continue():
            return
        _log.warning("Rebase failed after conflict resolution attempt; aborting rebase")
    git.rebase_abort()


def verify_checked(*, plan: Plan, agent: AgentService) -> list[PlanItem]:
    """Confirm [x] items are truly implemented via agent."""
    checked = [
        item for section in plan.sections for item in section.items if item.checked
    ]
    unverified: list[PlanItem] = []
    for item in checked:
        result = agent.run(
            prompt=f"Verify that this item is implemented in the codebase: {item.description}",
        )
        if "UNVERIFIED" in result.stdout:
            unverified.append(item)
    return unverified


def _render_plan(plan: Plan) -> str:
    """Render a Plan back to markdown text."""
    lines: list[str] = []
    lines.append(f"# {plan.title}")
    for section in plan.sections:
        lines.append("")
        lines.append(f"### {section.title}")
        for item in section.items:
            marker = "x" if item.checked else " "
            lines.append(f"- [{marker}] {item.description}")
    lines.append("")
    return "\n".join(lines)


def reorganize_findings(*, text: str, agent: AgentService) -> str:
    """Relocate Additional Findings items to proper sections via agent."""
    plan = parse_plan(text)
    findings_sections = [s for s in plan.sections if s.title == "Additional Findings"]
    if not findings_sections or not findings_sections[0].items:
        return text

    findings = findings_sections[0]
    other_sections = [s for s in plan.sections if s.title != "Additional Findings"]
    section_names = [s.title for s in other_sections]
    finding_descriptions = [item.description for item in findings.items]

    prompt = (
        "Map each finding to the best matching section.\n\n"
        "Findings:\n"
        + "\n".join(f"- {d}" for d in finding_descriptions)
        + "\n\nSections:\n"
        + "\n".join(f"- {s}" for s in section_names)
        + "\n\nRespond with a JSON object mapping finding description to section name."
    )
    result = agent.run(prompt=prompt)
    mapping: dict[str, str] = json.loads(result.stdout)

    section_additions: dict[str, list[PlanItem]] = {}
    moved: set[str] = set()
    for desc, target in mapping.items():
        section_additions.setdefault(target, []).append(PlanItem(description=desc))
        moved.add(desc)

    new_sections: list[Plan.Section] = []
    for section in plan.sections:
        if section.title == "Additional Findings":
            remaining = [i for i in section.items if i.description not in moved]
            if remaining:
                new_sections.append(Plan.Section(title=section.title, items=remaining))
            continue
        extras = section_additions.get(section.title, [])
        new_sections.append(
            Plan.Section(title=section.title, items=[*section.items, *extras])
        )

    return _render_plan(Plan(title=plan.title, sections=new_sections))


def find_gaps(*, plan_text: str, agent: AgentService) -> list[str]:
    """Identify missing plan items via agent."""
    result = agent.run(
        prompt=(
            "Identify any gaps or missing items in this plan:\n\n"
            + plan_text
            + "\n\nRespond with a JSON array of strings describing missing items. Return [] if none."
        ),
    )
    items: list[str] = json.loads(result.stdout)
    return items


def outer_loop(
    *,
    plan_path: Path,
    agent: AgentService,
    git: GitClient,
    config: WiggumConfig,
) -> None:
    """Orchestrate verify, gaps, reorganize, and inner_loop batches."""
    text = plan_path.read_text()
    plan = parse_plan(text)

    verify_checked(plan=plan, agent=agent)

    gaps = find_gaps(plan_text=text, agent=agent) or []
    for gap in gaps:
        text = append_todo(text, gap)
    if gaps:
        plan_path.write_text(text)

    text = plan_path.read_text()
    text = reorganize_findings(text=text, agent=agent) or text
    plan_path.write_text(text)

    cycles = 0
    while True:
        rebase_onto_base(git=git, config=config, agent=agent)

        plan = parse_plan(plan_path.read_text())
        if count_unchecked(plan) == 0:
            break
        if config.cycle_limit > 0 and cycles >= config.cycle_limit:
            break

        inner_loop(plan_path=plan_path, agent=agent, git=git, config=config)
        cycles += 1
