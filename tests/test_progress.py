from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from wiggum.progress import append_progress


class TestAppendProgressCreatesFile:
    def test_creates_file_when_missing(self, tmp_path: Path) -> None:
        progress_path = tmp_path / "PROGRESS.md"
        append_progress(progress_path, "First entry")
        assert progress_path.exists()

    def test_file_is_nonempty_after_first_append(self, tmp_path: Path) -> None:
        progress_path = tmp_path / "PROGRESS.md"
        append_progress(progress_path, "First entry")
        assert progress_path.read_text().strip() != ""


class TestAppendProgressContent:
    def test_entry_text_appears_in_file(self, tmp_path: Path) -> None:
        progress_path = tmp_path / "PROGRESS.md"
        append_progress(progress_path, "Implemented feature X")
        content = progress_path.read_text()
        assert "Implemented feature X" in content

    def test_entry_contains_iso_timestamp(self, tmp_path: Path) -> None:
        progress_path = tmp_path / "PROGRESS.md"
        append_progress(progress_path, "Some entry")
        content = progress_path.read_text()
        assert re.search(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}", content)

    def test_timestamp_matches_current_date(self, tmp_path: Path) -> None:
        progress_path = tmp_path / "PROGRESS.md"
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        append_progress(progress_path, "Dated entry")
        content = progress_path.read_text()
        assert today in content


class TestAppendProgressAccumulates:
    def test_appends_to_existing_content(self, tmp_path: Path) -> None:
        progress_path = tmp_path / "PROGRESS.md"
        append_progress(progress_path, "First")
        append_progress(progress_path, "Second")
        content = progress_path.read_text()
        assert "First" in content
        assert "Second" in content

    def test_preserves_prior_file_content(self, tmp_path: Path) -> None:
        progress_path = tmp_path / "PROGRESS.md"
        progress_path.write_text("# Progress\n\nExisting content\n")
        append_progress(progress_path, "New entry")
        content = progress_path.read_text()
        assert "Existing content" in content
        assert "New entry" in content

    def test_multiple_appends_produce_distinct_entries(self, tmp_path: Path) -> None:
        progress_path = tmp_path / "PROGRESS.md"
        entries = ["Alpha", "Beta", "Gamma"]
        for entry in entries:
            append_progress(progress_path, entry)
        content = progress_path.read_text()
        for entry in entries:
            assert content.count(entry) == 1
