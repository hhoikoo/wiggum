"""Tests for wiggum.prompts.load() -- importlib.resources-based prompt loader."""

import pytest

EXPECTED_PROMPTS = [
    "red",
    "green",
    "triage",
    "verify",
    "gaps",
    "reorganize",
    "select",
]


class TestLoadExists:
    def test_load_is_importable(self) -> None:
        from wiggum.prompts import load

        assert callable(load)

    def test_load_accepts_name_argument(self) -> None:
        from wiggum.prompts import load

        # Should accept a single positional string argument.
        load("red")


class TestLoadReturnsContent:
    @pytest.mark.parametrize("name", EXPECTED_PROMPTS)
    def test_returns_string(self, name: str) -> None:
        from wiggum.prompts import load

        result = load(name)
        assert isinstance(result, str)

    @pytest.mark.parametrize("name", EXPECTED_PROMPTS)
    def test_returns_nonempty(self, name: str) -> None:
        from wiggum.prompts import load

        result = load(name)
        assert len(result.strip()) > 0


class TestLoadErrorHandling:
    def test_unknown_name_raises_file_not_found(self) -> None:
        from wiggum.prompts import load

        with pytest.raises(FileNotFoundError):
            load("nonexistent_prompt_name")


class TestLoadUsesImportlibResources:
    @pytest.mark.parametrize("name", EXPECTED_PROMPTS)
    def test_content_matches_importlib_resources(self, name: str) -> None:
        """load() must return the same content as importlib.resources.files."""
        from importlib.resources import files

        from wiggum.prompts import load

        expected = (
            files("wiggum.prompts").joinpath(f"{name}.md").read_text(encoding="utf-8")
        )
        assert load(name) == expected

    def test_reads_with_utf8_encoding(self) -> None:
        from unittest.mock import MagicMock, patch

        mock_resource = MagicMock()
        mock_resource.read_text.return_value = "mock content"
        mock_files = MagicMock()
        mock_files.joinpath.return_value = mock_resource

        with patch("wiggum.prompts.files", return_value=mock_files):
            from wiggum.prompts import load

            load("red")
            mock_resource.read_text.assert_called_once_with(encoding="utf-8")
