"""Plan data structures and markdown parser."""

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlanItem:
    """A single checklist item in a plan section."""

    description: str
    checked: bool = False


@dataclass(frozen=True)
class Plan:
    """A parsed plan with a title and sections."""

    @dataclass(frozen=True)
    class Section:
        """A named group of plan items."""

        title: str
        items: list[PlanItem] = field(default_factory=list[PlanItem])

    title: str
    sections: list[Section] = field(default_factory=list[Section])


_ITEM_RE = re.compile(r"^- \[([ xX])\] (.+)$")


def parse_plan(text: str) -> Plan:
    """Parse a markdown plan into a Plan with sections and items."""
    title = ""
    sections: list[Plan.Section] = []
    current_section_title: str | None = None
    current_items: list[PlanItem] = []

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
            continue

        if stripped.startswith("### "):
            if current_section_title is not None:
                sections.append(
                    Plan.Section(title=current_section_title, items=current_items)
                )
            current_section_title = stripped[4:].strip()
            current_items = []
            continue

        m = _ITEM_RE.match(stripped)
        if m and current_section_title is not None:
            checked = m.group(1) in ("x", "X")
            current_items.append(
                PlanItem(description=m.group(2).strip(), checked=checked)
            )

    if current_section_title is not None:
        sections.append(Plan.Section(title=current_section_title, items=current_items))

    return Plan(title=title, sections=sections)


def get_unchecked(plan: Plan) -> list[PlanItem]:
    """Return all unchecked items across all sections."""
    return [
        item for section in plan.sections for item in section.items if not item.checked
    ]


def count_unchecked(plan: Plan) -> int:
    """Return the number of unchecked items across all sections."""
    return len(get_unchecked(plan))
