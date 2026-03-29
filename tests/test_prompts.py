from pathlib import Path

from wiggum.prompts import render_build_prompt, render_plan_prompt
from wiggum.templates import load_template, render_template

_IMPL_PATH = Path(".wiggum/implementation/42")


class TestLoadTemplate:
    def test_loads_plan_template(self):
        content = load_template("plan.md")
        assert "Planning Phase" in content
        assert "$issue_id" in content

    def test_loads_build_template(self):
        content = load_template("build.md")
        assert "Build Phase" in content
        assert "$task_description" in content


class TestRenderTemplate:
    def test_substitutes_plan_variables(self):
        result = render_template(
            "plan.md",
            issue_id="42",
            specs_content="Some specs here",
        )
        assert "**42**" in result
        assert "Some specs here" in result
        assert "$issue_id" not in result
        assert "$specs_content" not in result

    def test_substitutes_build_variables(self):
        result = render_template(
            "build.md",
            issue_id="42",
            task_description="Build the widget",
            quality_section="4. Run quality checks: `uv run pytest`",
        )
        assert "**42**" in result
        assert "Build the widget" in result
        assert "$task_description" not in result

    def test_safe_substitute_preserves_unknown_variables(self):
        result = render_template("plan.md", issue_id="42")
        assert "**42**" in result
        assert "$specs_content" in result

    def test_empty_quality_section(self):
        result = render_template(
            "build.md",
            issue_id="42",
            task_description="Build the widget",
            quality_section="",
        )
        assert "Build the widget" in result
        assert "$quality_section" not in result


class TestRenderPlanPrompt:
    def test_substitutes_issue_id_and_specs(self):
        result = render_plan_prompt(
            issue_id="99", specs_content="Build a widget", impl_path=_IMPL_PATH
        )
        assert "**99**" in result
        assert "Build a widget" in result
        assert "$issue_id" not in result
        assert "$specs_content" not in result

    def test_includes_impl_path(self):
        result = render_plan_prompt(
            issue_id="1", specs_content="", impl_path=_IMPL_PATH
        )
        assert str(_IMPL_PATH) in result
        assert "$impl_path" not in result

    def test_includes_planning_phase_header(self):
        result = render_plan_prompt(
            issue_id="1", specs_content="", impl_path=_IMPL_PATH
        )
        assert "Planning Phase" in result

    def test_includes_completion_signal(self):
        result = render_plan_prompt(
            issue_id="1", specs_content="", impl_path=_IMPL_PATH
        )
        assert '"status": "complete"' in result


class TestRenderBuildPrompt:
    def test_substitutes_issue_id_and_task(self):
        result = render_build_prompt(
            issue_id="42",
            task_description="Implement the parser",
            impl_path=_IMPL_PATH,
        )
        assert "**42**" in result
        assert "Implement the parser" in result
        assert "$issue_id" not in result
        assert "$task_description" not in result

    def test_includes_impl_path(self):
        result = render_build_prompt(
            issue_id="42",
            task_description="Do the thing",
            impl_path=_IMPL_PATH,
        )
        assert str(_IMPL_PATH) in result
        assert "$impl_path" not in result

    def test_quality_commands_rendered(self):
        result = render_build_prompt(
            issue_id="42",
            task_description="Do the thing",
            impl_path=_IMPL_PATH,
            quality_commands=["uv run pytest", "uv run pyright"],
        )
        assert "`uv run pytest`" in result
        assert "`uv run pyright`" in result
        assert "Run quality checks" in result

    def test_empty_quality_commands_omits_section(self):
        result = render_build_prompt(
            issue_id="42",
            task_description="Do the thing",
            impl_path=_IMPL_PATH,
            quality_commands=[],
        )
        assert "Run quality checks" not in result
        assert "$quality_section" not in result

    def test_none_quality_commands_omits_section(self):
        result = render_build_prompt(
            issue_id="42",
            task_description="Do the thing",
            impl_path=_IMPL_PATH,
        )
        assert "Run quality checks" not in result
        assert "$quality_section" not in result

    def test_includes_commit_skill_instruction(self):
        result = render_build_prompt(
            issue_id="42", task_description="Do the thing", impl_path=_IMPL_PATH
        )
        assert "/commit" in result

    def test_includes_build_phase_header(self):
        result = render_build_prompt(
            issue_id="42", task_description="Do the thing", impl_path=_IMPL_PATH
        )
        assert "Build Phase" in result
