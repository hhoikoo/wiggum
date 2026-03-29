from wiggum.prompts import render_build_prompt, render_plan_prompt
from wiggum.templates import load_template, render_template


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
        result = render_plan_prompt(issue_id="99", specs_content="Build a widget")
        assert "**99**" in result
        assert "Build a widget" in result
        assert "$issue_id" not in result
        assert "$specs_content" not in result

    def test_includes_planning_phase_header(self):
        result = render_plan_prompt(issue_id="1", specs_content="")
        assert "Planning Phase" in result

    def test_includes_completion_signal(self):
        result = render_plan_prompt(issue_id="1", specs_content="")
        assert '"status": "complete"' in result


class TestRenderBuildPrompt:
    def test_substitutes_issue_id_and_task(self):
        result = render_build_prompt(
            issue_id="42", task_description="Implement the parser"
        )
        assert "**42**" in result
        assert "Implement the parser" in result
        assert "$issue_id" not in result
        assert "$task_description" not in result

    def test_quality_commands_rendered(self):
        result = render_build_prompt(
            issue_id="42",
            task_description="Do the thing",
            quality_commands=["uv run pytest", "uv run pyright"],
        )
        assert "`uv run pytest`" in result
        assert "`uv run pyright`" in result
        assert "Run quality checks" in result

    def test_empty_quality_commands_omits_section(self):
        result = render_build_prompt(
            issue_id="42",
            task_description="Do the thing",
            quality_commands=[],
        )
        assert "Run quality checks" not in result
        assert "$quality_section" not in result

    def test_none_quality_commands_omits_section(self):
        result = render_build_prompt(
            issue_id="42",
            task_description="Do the thing",
        )
        assert "Run quality checks" not in result
        assert "$quality_section" not in result

    def test_includes_commit_skill_instruction(self):
        result = render_build_prompt(issue_id="42", task_description="Do the thing")
        assert "/commit" in result

    def test_includes_build_phase_header(self):
        result = render_build_prompt(issue_id="42", task_description="Do the thing")
        assert "Build Phase" in result
