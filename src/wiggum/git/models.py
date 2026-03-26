"""Data classes for git operations."""

from dataclasses import dataclass


@dataclass
class StatusEntry:
    """A single entry from git status output."""

    path: str


@dataclass
class LogEntry:
    """A single entry from git log output."""

    message: str
    hash: str
