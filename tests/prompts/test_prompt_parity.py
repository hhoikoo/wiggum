"""Tests that prompt .md files match the battle-tested prompts in scripts/ralph-minimal.sh.

Each prompt template must contain the same context-injection placeholders and
key instruction phrases as the reference script implementation.
"""

from pathlib import Path

import pytest

PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent / "src" / "wiggum" / "prompts"
)


def _read_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Preamble
# --------------------------------------------------------------------------- #


class TestPreamblePrompt:
    """preamble.md must exist and carry all 10 Ralph Loop Principles."""

    def test_preamble_file_exists(self) -> None:
        assert (PROMPTS_DIR / "preamble.md").is_file()

    def test_contains_ralph_loop_principles_heading(self) -> None:
        text = _read_prompt("preamble")
        assert "Ralph Loop Principles" in text

    @pytest.mark.parametrize(
        "phrase",
        [
            "exactly ONE thing",
            "Never expand scope",
            "NEW_TODO:",
            "Fresh context",
            "Minimal changes",
            "Python 3.14+",
            "uv run",
            "one-line docstring",
            "TYPE_CHECKING",
            "noqa: TC003",
            "runtime_checkable",
            "PEP 695",
            "ASCII only",
        ],
    )
    def test_contains_key_principle(self, phrase: str) -> None:
        text = _read_prompt("preamble")
        assert phrase in text


# --------------------------------------------------------------------------- #
# RED prompt
# --------------------------------------------------------------------------- #


class TestRedPromptPlaceholders:
    """red.md must have placeholders for all context the script injects."""

    def test_has_working_dir_placeholder(self) -> None:
        text = _read_prompt("red")
        assert "{working_dir}" in text

    def test_has_item_placeholder(self) -> None:
        text = _read_prompt("red")
        assert "{item}" in text

    def test_has_batch_items_placeholder(self) -> None:
        text = _read_prompt("red")
        assert "{batch_items}" in text

    def test_has_plan_text_placeholder(self) -> None:
        text = _read_prompt("red")
        assert "{plan_text}" in text


class TestRedPromptSections:
    """red.md must have the same section headings as the script."""

    @pytest.mark.parametrize(
        "heading",
        [
            "### Item to test",
            "### Other items being worked on in parallel",
            "### Existing plan",
            "### Instructions",
        ],
    )
    def test_has_section_heading(self, heading: str) -> None:
        text = _read_prompt("red")
        assert heading in text


# --------------------------------------------------------------------------- #
# GREEN prompt
# --------------------------------------------------------------------------- #


class TestGreenPromptPlaceholders:
    """green.md must have a working_dir placeholder like the script."""

    def test_has_working_dir_placeholder(self) -> None:
        text = _read_prompt("green")
        assert "{working_dir}" in text


# --------------------------------------------------------------------------- #
# Triage prompt
# --------------------------------------------------------------------------- #


class TestTriagePromptPlaceholders:
    """triage.md must have placeholders for test and lint output."""

    def test_has_test_output_placeholder(self) -> None:
        text = _read_prompt("triage")
        assert "{test_output}" in text

    def test_has_lint_output_placeholder(self) -> None:
        text = _read_prompt("triage")
        assert "{lint_output}" in text


class TestTriagePromptSections:
    """triage.md must have sections for test and lint output."""

    def test_has_test_output_section(self) -> None:
        text = _read_prompt("triage")
        assert "### Test output" in text

    def test_has_lint_output_section(self) -> None:
        text = _read_prompt("triage")
        assert "### Lint output" in text


# --------------------------------------------------------------------------- #
# Verify prompt
# --------------------------------------------------------------------------- #


class TestVerifyPromptPlaceholders:
    """verify.md must have placeholders for working dir and checked items."""

    def test_has_working_dir_placeholder(self) -> None:
        text = _read_prompt("verify")
        assert "{working_dir}" in text

    def test_has_checked_items_placeholder(self) -> None:
        text = _read_prompt("verify")
        assert "{checked_items}" in text


class TestVerifyPromptSections:
    """verify.md must have a section listing checked items."""

    def test_has_checked_items_section(self) -> None:
        text = _read_prompt("verify")
        assert "### Checked items to verify" in text


# --------------------------------------------------------------------------- #
# Gaps prompt
# --------------------------------------------------------------------------- #


class TestGapsPromptPlaceholders:
    """gaps.md must have placeholders for all context the script injects."""

    def test_has_working_dir_placeholder(self) -> None:
        text = _read_prompt("gaps")
        assert "{working_dir}" in text

    def test_has_unchecked_items_placeholder(self) -> None:
        text = _read_prompt("gaps")
        assert "{unchecked_items}" in text

    def test_has_recent_files_placeholder(self) -> None:
        text = _read_prompt("gaps")
        assert "{recent_files}" in text


class TestGapsPromptSections:
    """gaps.md must have sections matching the script."""

    def test_has_unchecked_items_section(self) -> None:
        text = _read_prompt("gaps")
        assert "### Current plan (unchecked items only)" in text

    def test_has_recent_files_section(self) -> None:
        text = _read_prompt("gaps")
        assert "### Recently changed source files" in text


class TestGapsPromptInstructions:
    """gaps.md must include the full-codebase-scan restriction from the script."""

    def test_no_full_codebase_scan_instruction(self) -> None:
        text = _read_prompt("gaps")
        assert "Do NOT do a full codebase scan" in text


# --------------------------------------------------------------------------- #
# Reorganize prompt
# --------------------------------------------------------------------------- #


class TestReorganizePromptPlaceholders:
    """reorganize.md must have a placeholder for the current plan."""

    def test_has_plan_text_placeholder(self) -> None:
        text = _read_prompt("reorganize")
        assert "{plan_text}" in text


class TestReorganizePromptSections:
    """reorganize.md must have a section for the current plan."""

    def test_has_current_plan_section(self) -> None:
        text = _read_prompt("reorganize")
        assert "### Current plan" in text


# --------------------------------------------------------------------------- #
# Select prompt
# --------------------------------------------------------------------------- #


class TestSelectPromptPlaceholders:
    """select.md must have placeholders for batch size and item list."""

    def test_has_batch_size_placeholder(self) -> None:
        text = _read_prompt("select")
        assert "{batch_size}" in text

    def test_has_items_placeholder(self) -> None:
        text = _read_prompt("select")
        assert "{items}" in text
