from wiggum.git import LogEntry, StatusEntry


class TestStatusEntry:
    def test_path_field(self) -> None:
        entry = StatusEntry(path="src/main.py")
        assert entry.path == "src/main.py"

    def test_is_dataclass(self) -> None:
        import dataclasses

        assert dataclasses.is_dataclass(StatusEntry)


class TestLogEntry:
    def test_message_field(self) -> None:
        entry = LogEntry(message="fix: something", hash="abc123")
        assert entry.message == "fix: something"

    def test_hash_field(self) -> None:
        entry = LogEntry(message="fix: something", hash="abc123")
        assert entry.hash == "abc123"

    def test_is_dataclass(self) -> None:
        import dataclasses

        assert dataclasses.is_dataclass(LogEntry)
