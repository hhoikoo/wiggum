"""Priority selection via agent-driven dependency ordering."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wiggum.agent import AgentService
    from wiggum.plan import PlanItem

_NUMBERED_ITEM_RE = re.compile(r"^\d+\.\s+(.+)$", re.MULTILINE)

_SYSTEM_PROMPT = "You are a dependency-order planner. Given a list of tasks, return them numbered in the order they should be completed based on dependency relationships. Return only the numbered list, nothing else."


def select_items(
    *,
    items: Sequence[PlanItem],
    agent: AgentService,
    count: int,
) -> list[PlanItem]:
    """Pick top N items by dependency order using an agent."""
    if not items:
        return []

    descriptions = "\n".join(f"- {item.description}" for item in items)
    prompt = f"Order these tasks by dependency (most independent first), return the top {count}:\n\n{descriptions}"

    result = agent.run(prompt=prompt, system_prompt=_SYSTEM_PROMPT)

    by_description = {item.description: item for item in items}
    ordered: list[PlanItem] = []

    for match in _NUMBERED_ITEM_RE.finditer(result.stdout):
        desc = match.group(1).strip()
        if desc in by_description and by_description[desc] not in ordered:
            ordered.append(by_description[desc])

    return ordered[:count]
