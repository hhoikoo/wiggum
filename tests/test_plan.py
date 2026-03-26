from __future__ import annotations

import textwrap

import pytest

from wiggum.plan import (
    Plan,
    PlanItem,
    append_todo,
    count_unchecked,
    get_unchecked,
    mark_checked,
    parse_plan,
)

SIMPLE_PLAN = textwrap.dedent("""\
    # Phase 1: Core Ralph Loop

    ### Dependencies & Build
    - [ ] Add cyclopts and pydantic to project dependencies
    - [x] Set up project structure

    ### Git Package
    - [ ] GitPort Protocol in src/wiggum/git/__init__.py
    - [ ] ShellGitAdapter in src/wiggum/git/shell.py
""")

EMPTY_PLAN = textwrap.dedent("""\
    # My Plan

    ### Empty Section
""")

SINGLE_ITEM_PLAN = textwrap.dedent("""\
    # Plan

    ### Build
    - [ ] Install dependencies
""")


class TestPlanItem:
    """Tests for PlanItem dataclass construction and fields."""

    def test_unchecked_by_default(self) -> None:
        item = PlanItem(description="Install deps")
        assert item.checked is False

    def test_checked_item(self) -> None:
        item = PlanItem(description="Done task", checked=True)
        assert item.checked is True
        assert item.description == "Done task"

    def test_frozen(self) -> None:
        item = PlanItem(description="Immutable")
        with pytest.raises(AttributeError):
            item.description = "Changed"  # type: ignore[misc]


class TestPlanSection:
    """Tests for Plan.Section dataclass construction and fields."""

    def test_empty_items(self) -> None:
        section = Plan.Section(title="Empty", items=[])
        assert section.title == "Empty"
        assert section.items == []

    def test_section_with_items(self) -> None:
        items = [
            PlanItem(description="A"),
            PlanItem(description="B", checked=True),
        ]
        section = Plan.Section(title="Build", items=items)
        assert len(section.items) == 2
        assert section.items[0].description == "A"
        assert section.items[1].checked is True

    def test_frozen(self) -> None:
        section = Plan.Section(title="Locked", items=[])
        with pytest.raises(AttributeError):
            section.title = "Changed"  # type: ignore[misc]


class TestPlan:
    """Tests for Plan dataclass construction and fields."""

    def test_empty_plan(self) -> None:
        plan = Plan(title="Empty", sections=[])
        assert plan.title == "Empty"
        assert plan.sections == []

    def test_plan_with_sections(self) -> None:
        sec = Plan.Section(
            title="Git",
            items=[PlanItem(description="Create port")],
        )
        plan = Plan(title="Phase 1", sections=[sec])
        assert len(plan.sections) == 1
        assert plan.sections[0].title == "Git"
        assert plan.sections[0].items[0].description == "Create port"

    def test_frozen(self) -> None:
        plan = Plan(title="Locked", sections=[])
        with pytest.raises(AttributeError):
            plan.title = "Changed"  # type: ignore[misc]


class TestParsePlanSections:
    """Tests for section extraction from plan markdown."""

    def test_extracts_section_names(self) -> None:
        plan = parse_plan(SIMPLE_PLAN)
        names = [s.title for s in plan.sections]
        assert names == ["Dependencies & Build", "Git Package"]

    def test_empty_section_has_no_items(self) -> None:
        plan = parse_plan(EMPTY_PLAN)
        assert len(plan.sections) == 1
        assert plan.sections[0].items == []

    def test_section_count(self) -> None:
        plan = parse_plan(SIMPLE_PLAN)
        assert len(plan.sections) == 2


class TestParsePlanItems:
    """Tests for item extraction within sections."""

    def test_unchecked_item_is_not_checked(self) -> None:
        plan = parse_plan(SIMPLE_PLAN)
        first_item = plan.sections[0].items[0]
        assert first_item.checked is False

    def test_checked_item_is_checked(self) -> None:
        plan = parse_plan(SIMPLE_PLAN)
        second_item = plan.sections[0].items[1]
        assert second_item.checked is True

    def test_item_description_extracted(self) -> None:
        plan = parse_plan(SIMPLE_PLAN)
        first_item = plan.sections[0].items[0]
        assert (
            first_item.description
            == "Add cyclopts and pydantic to project dependencies"
        )

    def test_items_assigned_to_correct_section(self) -> None:
        plan = parse_plan(SIMPLE_PLAN)
        dep_items = plan.sections[0].items
        git_items = plan.sections[1].items
        assert len(dep_items) == 2
        assert len(git_items) == 2


class TestParsePlanReturnType:
    """Tests for the Plan object returned by parse_plan."""

    def test_returns_plan_instance(self) -> None:
        plan = parse_plan(SIMPLE_PLAN)
        assert isinstance(plan, Plan)

    def test_plan_title_extracted(self) -> None:
        plan = parse_plan(SIMPLE_PLAN)
        assert plan.title == "Phase 1: Core Ralph Loop"

    def test_items_are_plan_item_instances(self) -> None:
        plan = parse_plan(SINGLE_ITEM_PLAN)
        item = plan.sections[0].items[0]
        assert isinstance(item, PlanItem)


class TestParsePlanEdgeCases:
    """Tests for edge-case plan content."""

    def test_no_sections_yields_empty_list(self) -> None:
        plan = parse_plan("# Just a title\n")
        assert plan.sections == []

    def test_no_title_yields_empty_string(self) -> None:
        plan = parse_plan("### Section\n- [ ] item\n")
        assert plan.title == ""


ALL_UNCHECKED_PLAN = textwrap.dedent("""\
    # Plan

    ### Build
    - [ ] Task A
    - [ ] Task B

    ### Test
    - [ ] Task C
""")

ALL_CHECKED_PLAN = textwrap.dedent("""\
    # Plan

    ### Build
    - [x] Task A
    - [x] Task B
""")

MIXED_PLAN = textwrap.dedent("""\
    # Plan

    ### Build
    - [x] Done task
    - [ ] Pending task A

    ### Test
    - [ ] Pending task B
    - [x] Another done task
""")


class TestGetUnchecked:
    """Tests for get_unchecked query helper."""

    def test_returns_all_items_when_none_checked(self) -> None:
        plan = parse_plan(ALL_UNCHECKED_PLAN)
        unchecked = get_unchecked(plan)
        assert len(unchecked) == 3

    def test_returns_empty_when_all_checked(self) -> None:
        plan = parse_plan(ALL_CHECKED_PLAN)
        unchecked = get_unchecked(plan)
        assert unchecked == []

    def test_returns_only_unchecked_items(self) -> None:
        plan = parse_plan(MIXED_PLAN)
        unchecked = get_unchecked(plan)
        descriptions = [item.description for item in unchecked]
        assert descriptions == ["Pending task A", "Pending task B"]

    def test_returned_items_are_plan_items(self) -> None:
        plan = parse_plan(ALL_UNCHECKED_PLAN)
        unchecked = get_unchecked(plan)
        assert all(isinstance(item, PlanItem) for item in unchecked)

    def test_empty_plan_returns_empty(self) -> None:
        plan = parse_plan(EMPTY_PLAN)
        unchecked = get_unchecked(plan)
        assert unchecked == []

    def test_preserves_item_descriptions(self) -> None:
        plan = parse_plan(SINGLE_ITEM_PLAN)
        unchecked = get_unchecked(plan)
        assert len(unchecked) == 1
        assert unchecked[0].description == "Install dependencies"


class TestCountUnchecked:
    """Tests for count_unchecked query helper."""

    def test_counts_all_when_none_checked(self) -> None:
        plan = parse_plan(ALL_UNCHECKED_PLAN)
        assert count_unchecked(plan) == 3

    def test_zero_when_all_checked(self) -> None:
        plan = parse_plan(ALL_CHECKED_PLAN)
        assert count_unchecked(plan) == 0

    def test_counts_only_unchecked(self) -> None:
        plan = parse_plan(MIXED_PLAN)
        assert count_unchecked(plan) == 2

    def test_empty_plan_returns_zero(self) -> None:
        plan = parse_plan(EMPTY_PLAN)
        assert count_unchecked(plan) == 0

    def test_consistent_with_get_unchecked(self) -> None:
        plan = parse_plan(MIXED_PLAN)
        assert count_unchecked(plan) == len(get_unchecked(plan))


PLAN_WITH_FINDINGS = textwrap.dedent("""\
    # Phase 1

    ### Build
    - [x] Set up project

    ### Additional Findings
    - [ ] Existing finding
""")

PLAN_WITHOUT_FINDINGS = textwrap.dedent("""\
    # Phase 1

    ### Build
    - [x] Set up project
    - [ ] Add dependencies
""")


ADDITIONAL_FINDINGS_TITLE = "Additional Findings"


class TestAppendTodo:
    """Tests for append_todo adding items under Additional Findings."""

    def test_appends_to_existing_findings_section(self) -> None:
        result = append_todo(PLAN_WITH_FINDINGS, "New finding")
        plan = parse_plan(result)
        findings = [s for s in plan.sections if s.title == ADDITIONAL_FINDINGS_TITLE]
        assert len(findings) == 1
        descriptions = [item.description for item in findings[0].items]
        assert "Existing finding" in descriptions
        assert "New finding" in descriptions

    def test_creates_findings_section_when_missing(self) -> None:
        result = append_todo(PLAN_WITHOUT_FINDINGS, "Discovered issue")
        plan = parse_plan(result)
        findings = [s for s in plan.sections if s.title == ADDITIONAL_FINDINGS_TITLE]
        assert len(findings) == 1
        assert findings[0].items[0].description == "Discovered issue"

    def test_appended_item_is_unchecked(self) -> None:
        result = append_todo(PLAN_WITHOUT_FINDINGS, "Some todo")
        plan = parse_plan(result)
        findings = [s for s in plan.sections if s.title == ADDITIONAL_FINDINGS_TITLE]
        assert findings[0].items[0].checked is False

    def test_preserves_existing_sections(self) -> None:
        result = append_todo(PLAN_WITHOUT_FINDINGS, "New finding")
        plan = parse_plan(result)
        build = [s for s in plan.sections if s.title == "Build"]
        assert len(build) == 1
        assert len(build[0].items) == 2

    def test_preserves_plan_title(self) -> None:
        result = append_todo(PLAN_WITHOUT_FINDINGS, "New finding")
        plan = parse_plan(result)
        assert plan.title == "Phase 1"

    def test_multiple_appends_accumulate(self) -> None:
        result = append_todo(PLAN_WITHOUT_FINDINGS, "First")
        result = append_todo(result, "Second")
        plan = parse_plan(result)
        findings = [s for s in plan.sections if s.title == ADDITIONAL_FINDINGS_TITLE]
        descriptions = [item.description for item in findings[0].items]
        assert descriptions == ["First", "Second"]

    def test_does_not_duplicate_findings_section(self) -> None:
        result = append_todo(PLAN_WITH_FINDINGS, "Another")
        plan = parse_plan(result)
        findings = [s for s in plan.sections if s.title == ADDITIONAL_FINDINGS_TITLE]
        assert len(findings) == 1

    def test_result_is_valid_markdown(self) -> None:
        result = append_todo(PLAN_WITHOUT_FINDINGS, "Check this")
        assert "- [ ] Check this" in result


class TestMarkChecked:
    """Tests for mark_checked flipping [ ] to [x]."""

    def test_marks_unchecked_item(self) -> None:
        result = mark_checked(SINGLE_ITEM_PLAN, "Install dependencies")
        assert "- [x] Install dependencies" in result

    def test_original_unchecked_marker_removed(self) -> None:
        result = mark_checked(SINGLE_ITEM_PLAN, "Install dependencies")
        assert "- [ ] Install dependencies" not in result

    def test_only_marks_matching_item(self) -> None:
        result = mark_checked(ALL_UNCHECKED_PLAN, "Task A")
        plan = parse_plan(result)
        task_a = [
            item
            for section in plan.sections
            for item in section.items
            if item.description == "Task A"
        ]
        task_b = [
            item
            for section in plan.sections
            for item in section.items
            if item.description == "Task B"
        ]
        assert task_a[0].checked is True
        assert task_b[0].checked is False

    def test_preserves_other_sections(self) -> None:
        result = mark_checked(ALL_UNCHECKED_PLAN, "Task A")
        plan = parse_plan(result)
        test_section = [s for s in plan.sections if s.title == "Test"]
        assert len(test_section) == 1
        assert test_section[0].items[0].checked is False

    def test_preserves_plan_title(self) -> None:
        result = mark_checked(
            SIMPLE_PLAN, "Add cyclopts and pydantic to project dependencies"
        )
        plan = parse_plan(result)
        assert plan.title == "Phase 1: Core Ralph Loop"

    def test_preserves_already_checked_items(self) -> None:
        result = mark_checked(
            SIMPLE_PLAN, "Add cyclopts and pydantic to project dependencies"
        )
        plan = parse_plan(result)
        checked_descriptions = [
            item.description
            for section in plan.sections
            for item in section.items
            if item.checked
        ]
        assert "Set up project structure" in checked_descriptions

    def test_raises_on_missing_item(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            mark_checked(SIMPLE_PLAN, "Nonexistent task")

    def test_raises_on_already_checked_item(self) -> None:
        with pytest.raises(ValueError, match="already checked"):
            mark_checked(SIMPLE_PLAN, "Set up project structure")

    def test_roundtrip_with_parse_plan(self) -> None:
        result = mark_checked(MIXED_PLAN, "Pending task A")
        plan = parse_plan(result)
        unchecked = get_unchecked(plan)
        descriptions = [item.description for item in unchecked]
        assert "Pending task A" not in descriptions
        assert "Pending task B" in descriptions
