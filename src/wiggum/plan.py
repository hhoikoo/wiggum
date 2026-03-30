"""IMPLEMENTATION_PLAN.md parser with checkbox operations."""

import re
from dataclasses import dataclass, field
from pathlib import Path

_CHECKBOX_RE = re.compile(r"^(\s*-\s*\[)([ x])(\]\s*.+)$", re.MULTILINE)


@dataclass
class Task:
    """A single checkbox item from IMPLEMENTATION_PLAN.md."""

    line_number: int
    description: str
    checked: bool


@dataclass
class PlanState:
    """Mutable state for an IMPLEMENTATION_PLAN.md file."""

    path: Path
    tasks: list[Task]
    _marked_lines: set[int] = field(default_factory=set[int])

    def top_unchecked(self) -> Task | None:
        """Return the first unchecked task, or None if all are complete."""
        for task in self.tasks:
            if not task.checked:
                return task
        return None

    def all_complete(self) -> bool:
        """Return True when every task is checked."""
        return all(task.checked for task in self.tasks)

    def mark_complete(self, line_number: int) -> None:
        """Mark the task at *line_number* as complete and track it for potential reset."""
        for task in self.tasks:
            if task.line_number == line_number:
                task.checked = True
                self._marked_lines.add(line_number)
                return
        msg = f"no task at line {line_number}"
        raise ValueError(msg)

    def reset_uncommitted(self) -> None:
        """Reset marks added via mark_complete back to unchecked."""
        for task in self.tasks:
            if task.line_number in self._marked_lines:
                task.checked = False
        self._marked_lines.clear()

    def write(self) -> None:
        """Write the current state back to the file."""
        lines = self.path.read_text().splitlines(keepends=True)
        for task in self.tasks:
            idx = task.line_number - 1
            line = lines[idx]
            m = _CHECKBOX_RE.match(line.rstrip("\n"))
            if m:
                mark = "x" if task.checked else " "
                replacement = f"{m.group(1)}{mark}{m.group(3)}"
                # preserve original line ending
                if line.endswith("\n"):
                    replacement += "\n"
                lines[idx] = replacement
        self.path.write_text("".join(lines))


def parse_plan(path: Path) -> PlanState:
    """Parse IMPLEMENTATION_PLAN.md into a PlanState."""
    text = path.read_text()
    tasks: list[Task] = []
    for i, line in enumerate(text.splitlines(), start=1):
        m = _CHECKBOX_RE.match(line)
        if m:
            checked = m.group(2) == "x"
            description = m.group(3).lstrip("] ").strip()
            tasks.append(Task(line_number=i, description=description, checked=checked))
    return PlanState(path=path, tasks=tasks, _marked_lines=set())
