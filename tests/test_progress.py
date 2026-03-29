from datetime import UTC, datetime

from wiggum.progress import Outcome, _count_iterations, append_iteration

_EXISTING_PROGRESS = """\
# Progress

## Iteration 1 (2026-03-29T10:00:00)
- **Task:** Set up project structure
- **Outcome:** pass

## Iteration 2 (2026-03-29T11:00:00)
- **Task:** Write initial tests
- **Outcome:** fail

"""

_TS = datetime(2026, 3, 29, 12, 0, 0, tzinfo=UTC)


class TestCountIterations:
    def test_counts_existing_headings(self):
        assert _count_iterations(_EXISTING_PROGRESS) == 2

    def test_zero_when_no_headings(self):
        assert _count_iterations("# Progress\n\n") == 0

    def test_zero_for_empty_string(self):
        assert _count_iterations("") == 0


class TestAppendIteration:
    def test_appends_entry_to_existing_file(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        progress.write_text(_EXISTING_PROGRESS)
        append_iteration(
            path=progress,
            task="Implement core logic",
            outcome=Outcome.PASS,
            timestamp=_TS,
        )
        content = progress.read_text()
        assert "## Iteration 3 (2026-03-29T12:00:00)" in content
        assert "- **Task:** Implement core logic" in content
        assert "- **Outcome:** pass" in content

    def test_preserves_existing_content(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        progress.write_text(_EXISTING_PROGRESS)
        append_iteration(
            path=progress,
            task="New task",
            outcome=Outcome.PASS,
            timestamp=_TS,
        )
        content = progress.read_text()
        assert content.startswith(_EXISTING_PROGRESS)

    def test_first_iteration_on_empty_file(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        progress.write_text("# Progress\n\n")
        append_iteration(
            path=progress,
            task="First task",
            outcome=Outcome.PASS,
            timestamp=_TS,
        )
        content = progress.read_text()
        assert "## Iteration 1 (2026-03-29T12:00:00)" in content

    def test_creates_file_if_missing(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        append_iteration(
            path=progress,
            task="Bootstrap",
            outcome=Outcome.PASS,
            timestamp=_TS,
        )
        assert progress.exists()
        content = progress.read_text()
        assert "## Iteration 1" in content

    def test_fail_outcome(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        progress.write_text("")
        append_iteration(
            path=progress,
            task="Broken task",
            outcome=Outcome.FAIL,
            timestamp=_TS,
        )
        assert "- **Outcome:** fail" in progress.read_text()

    def test_interrupted_outcome(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        progress.write_text("")
        append_iteration(
            path=progress,
            task="Interrupted task",
            outcome=Outcome.INTERRUPTED,
            timestamp=_TS,
        )
        assert "- **Outcome:** interrupted" in progress.read_text()

    def test_includes_patterns(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        progress.write_text("")
        append_iteration(
            path=progress,
            task="Discovery task",
            outcome=Outcome.PASS,
            patterns=["Use pathlib for paths", "tmp_path for tests"],
            timestamp=_TS,
        )
        content = progress.read_text()
        assert "- **Patterns:**" in content
        assert "  - Use pathlib for paths" in content
        assert "  - tmp_path for tests" in content

    def test_omits_patterns_section_when_none(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        progress.write_text("")
        append_iteration(
            path=progress,
            task="No patterns",
            outcome=Outcome.PASS,
            timestamp=_TS,
        )
        assert "**Patterns:**" not in progress.read_text()

    def test_omits_patterns_section_when_empty_list(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        progress.write_text("")
        append_iteration(
            path=progress,
            task="Empty patterns",
            outcome=Outcome.PASS,
            patterns=[],
            timestamp=_TS,
        )
        assert "**Patterns:**" not in progress.read_text()

    def test_sequential_appends_increment_number(self, tmp_path):
        progress = tmp_path / "PROGRESS.md"
        progress.write_text("# Progress\n\n")
        for i in range(3):
            append_iteration(
                path=progress,
                task=f"Task {i + 1}",
                outcome=Outcome.PASS,
                timestamp=_TS,
            )
        content = progress.read_text()
        assert "## Iteration 1" in content
        assert "## Iteration 2" in content
        assert "## Iteration 3" in content
