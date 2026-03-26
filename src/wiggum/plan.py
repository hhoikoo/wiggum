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


_ADDITIONAL_FINDINGS_HEADER = "### Additional Findings"


def append_todo(text: str, description: str) -> str:
    """Add an unchecked item under the Additional Findings section."""
    new_item = f"- [ ] {description}"

    if _ADDITIONAL_FINDINGS_HEADER in text:
        lines = text.splitlines(keepends=True)
        insert_idx = len(lines)
        in_section = False
        for i, line in enumerate(lines):
            if line.strip() == _ADDITIONAL_FINDINGS_HEADER:
                in_section = True
                continue
            if in_section:
                if line.strip().startswith("### "):
                    insert_idx = i
                    break
                if _ITEM_RE.match(line.strip()):
                    insert_idx = i + 1
        lines.insert(insert_idx, new_item + "\n")
        return "".join(lines)

    stripped = text.rstrip("\n")
    return f"{stripped}\n\n{_ADDITIONAL_FINDINGS_HEADER}\n{new_item}\n"


def mark_checked(text: str, description: str) -> str:
    """Flip a specific item from [ ] to [x] in plan markdown."""
    unchecked_target = f"- [ ] {description}"
    checked_target = f"- [x] {description}"

    if checked_target in text or f"- [X] {description}" in text:
        msg = f"Item already checked: {description}"
        raise ValueError(msg)

    if unchecked_target not in text:
        msg = f"Item not found: {description}"
        raise ValueError(msg)

    return text.replace(unchecked_target, checked_target, 1)


_CHECKED_RE = re.compile(r"^\s*- \[[xX]\] .+$")


def remove_checked(text: str) -> str:
    """Delete all checked items from plan markdown."""
    lines = text.splitlines(keepends=True)
    return "".join(line for line in lines if not _CHECKED_RE.match(line))
