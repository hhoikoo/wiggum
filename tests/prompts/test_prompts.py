import importlib

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


class TestPromptsPackage:
    def test_prompts_package_is_importable(self):
        mod = importlib.import_module("wiggum.prompts")
        assert mod is not None

    def test_prompts_package_has_dunder_path(self):
        mod = importlib.import_module("wiggum.prompts")
        assert hasattr(mod, "__path__")


class TestLoadPrompt:
    def test_load_prompt_is_callable(self):
        from wiggum.prompts import load_prompt

        assert callable(load_prompt)

    @pytest.mark.parametrize("name", EXPECTED_PROMPTS)
    def test_load_prompt_returns_string(self, name):
        from wiggum.prompts import load_prompt

        result = load_prompt(name)
        assert isinstance(result, str)

    @pytest.mark.parametrize("name", EXPECTED_PROMPTS)
    def test_load_prompt_returns_nonempty(self, name):
        from wiggum.prompts import load_prompt

        result = load_prompt(name)
        assert len(result.strip()) > 0

    def test_load_prompt_unknown_name_raises(self):
        from wiggum.prompts import load_prompt

        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent")


class TestPromptFilesExist:
    @pytest.mark.parametrize("name", EXPECTED_PROMPTS)
    def test_markdown_file_is_package_resource(self, name):
        from importlib.resources import files

        resource = files("wiggum.prompts").joinpath(f"{name}.md")
        assert resource.is_file()
