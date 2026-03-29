"""Prompt rendering for plan and build phases."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wiggum.templates import render_template

if TYPE_CHECKING:
    from collections.abc import Sequence

_QUALITY_SECTION_TEMPLATE = "4. Run quality checks:\n{commands}"


def render_plan_prompt(
    *,
    issue_id: str,
    specs_content: str,
) -> str:
    """Render the plan-phase prompt with specs and issue context."""
    return render_template(
        "plan.md",
        issue_id=issue_id,
        specs_content=specs_content,
    )


def _format_quality_section(quality_commands: Sequence[str]) -> str:
    """Format quality commands into a numbered instruction section.

    Returns an empty string when *quality_commands* is empty, which omits
    the quality instructions from the rendered prompt.
    """
    if not quality_commands:
        return ""
    commands = "\n".join(f"   - `{cmd}`" for cmd in quality_commands)
    return _QUALITY_SECTION_TEMPLATE.format(commands=commands)


def render_build_prompt(
    *,
    issue_id: str,
    task_description: str,
    quality_commands: Sequence[str] | None = None,
) -> str:
    """Render the build-phase prompt with task info and quality commands."""
    quality_section = _format_quality_section(quality_commands or [])
    return render_template(
        "build.md",
        issue_id=issue_id,
        task_description=task_description,
        quality_section=quality_section,
    )
