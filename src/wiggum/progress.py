"""PROGRESS.md heading-per-iteration writer."""

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_ITERATION_RE = re.compile(r"^## Iteration \d+", re.MULTILINE)


class Outcome(StrEnum):
    """Outcome of a build iteration."""

    PASS = "pass"  # noqa: S105
    FAIL = "fail"
    INTERRUPTED = "interrupted"


def _count_iterations(text: str) -> int:
    """Count existing ``## Iteration N`` headings in *text*."""
    return len(_ITERATION_RE.findall(text))


def append_iteration(
    *,
    path: Path,
    task: str,
    outcome: Outcome,
    patterns: list[str] | None = None,
    timestamp: datetime | None = None,
) -> None:
    """Append a heading-per-iteration entry to a PROGRESS.md file.

    Append-only: existing content is never modified.
    """
    text = path.read_text() if path.exists() else ""
    n = _count_iterations(text) + 1
    ts = timestamp or datetime.now(tz=UTC)
    iso = ts.strftime("%Y-%m-%dT%H:%M:%S")

    lines = [
        f"## Iteration {n} ({iso})\n",
        f"- **Task:** {task}\n",
        f"- **Outcome:** {outcome.value}\n",
    ]
    if patterns:
        lines.append("- **Patterns:**\n")
        lines.extend(f"  - {p}\n" for p in patterns)
    lines.append("\n")

    with path.open("a") as f:
        f.write("".join(lines))
