"""Progress tracking for the ralph loop."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def append_progress(path: Path, entry: str) -> None:
    """Append a timestamped entry to a progress file."""
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%S")
    line = f"- {timestamp} {entry}\n"
    with path.open("a") as f:
        f.write(line)
