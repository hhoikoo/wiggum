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
