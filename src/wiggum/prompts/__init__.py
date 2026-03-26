"""Agent prompt loading and building."""

from importlib.resources import files
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def load_prompt(name: str) -> str:
    """Load a prompt markdown file by name."""
    resource = files(__name__).joinpath(f"{name}.md")
    return resource.read_text(encoding="utf-8")


def build_green_prompt(
    *,
    plan_text: str,
    tasks: Sequence[str],
    is_fix_round: bool = False,
) -> str:
    """Build the GREEN phase prompt from plan text and task list."""
    header = "### Failures to fix" if is_fix_round else "### What to implement"

    task_block = "\n".join(f"- {t}" for t in tasks)

    return (
        f"## Task: Implement (GREEN)\n\n"
        f"{header}\n\n"
        f"{task_block}\n\n"
        f"### Existing plan (do NOT output NEW_TODO for anything already listed here)\n\n"
        f"{plan_text}\n\n"
        f"### Instructions\n\n"
        f"1. Read relevant tests and source code to understand what is expected.\n"
        f"2. Write the MINIMUM code to make it work.\n"
        f"3. Run `uv run ruff check --fix --unsafe-fixes` on files you changed and fix any remaining lint errors.\n"
        f"4. Do NOT run pytest -- the harness handles that.\n"
        f"5. Do NOT write new tests.\n"
        f"6. Do NOT refactor unrelated code.\n"
        f"7. Only output NEW_TODO: for gaps that are NOT already in the plan above.\n"
    )
