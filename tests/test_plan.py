import pytest

from wiggum.plan import parse_plan

_SAMPLE_PLAN = """\
# Implementation Plan

## Tasks

- [ ] Set up project structure
- [x] Write initial tests
- [ ] Implement core logic
- [ ] Add error handling
"""


class TestParsePlan:
    def test_parses_checkbox_items(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        assert len(state.tasks) == 4

    def test_captures_checked_state(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        assert not state.tasks[0].checked
        assert state.tasks[1].checked
        assert not state.tasks[2].checked

    def test_captures_descriptions(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        assert state.tasks[0].description == "Set up project structure"
        assert state.tasks[1].description == "Write initial tests"

    def test_captures_line_numbers(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        assert state.tasks[0].line_number == 5
        assert state.tasks[3].line_number == 8

    def test_empty_file_returns_no_tasks(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("# Implementation Plan\n\n## Tasks\n\n")
        state = parse_plan(plan_file)
        assert state.tasks == []

    def test_ignores_non_checkbox_lines(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("# Title\n\nSome prose\n\n- [ ] Only task\n")
        state = parse_plan(plan_file)
        assert len(state.tasks) == 1


class TestTopUnchecked:
    def test_returns_first_unchecked(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        task = state.top_unchecked()
        assert task is not None
        assert task.description == "Set up project structure"

    def test_skips_checked_tasks(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("- [x] Done\n- [ ] Next\n")
        state = parse_plan(plan_file)
        task = state.top_unchecked()
        assert task is not None
        assert task.description == "Next"

    def test_returns_none_when_all_complete(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("- [x] Done\n- [x] Also done\n")
        state = parse_plan(plan_file)
        assert state.top_unchecked() is None


class TestAllComplete:
    def test_false_when_unchecked_exist(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        assert not state.all_complete()

    def test_true_when_all_checked(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("- [x] Done\n- [x] Also done\n")
        state = parse_plan(plan_file)
        assert state.all_complete()

    def test_true_when_no_tasks(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text("# Empty plan\n")
        state = parse_plan(plan_file)
        assert state.all_complete()


class TestMarkComplete:
    def test_marks_task_checked(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        state.mark_complete(5)
        assert state.tasks[0].checked

    def test_tracks_marked_lines(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        state.mark_complete(5)
        assert 5 in state._marked_lines

    def test_raises_for_invalid_line(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        with pytest.raises(ValueError, match="no task at line 999"):
            state.mark_complete(999)


class TestResetUncommitted:
    def test_resets_marked_tasks(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        state.mark_complete(5)
        assert state.tasks[0].checked
        state.reset_uncommitted()
        assert not state.tasks[0].checked

    def test_preserves_originally_checked(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        # task at line 6 was already checked in the file
        state.mark_complete(5)
        state.reset_uncommitted()
        assert state.tasks[1].checked  # originally checked, untouched

    def test_clears_marked_lines_set(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        state.mark_complete(5)
        state.reset_uncommitted()
        assert len(state._marked_lines) == 0


class TestWrite:
    def test_writes_marks_to_file(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        state.mark_complete(5)
        state.write()
        content = plan_file.read_text()
        assert "- [x] Set up project structure" in content

    def test_preserves_unchecked_tasks(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        state.mark_complete(5)
        state.write()
        content = plan_file.read_text()
        assert "- [ ] Implement core logic" in content

    def test_roundtrip_preserves_content(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        state.write()
        assert plan_file.read_text() == _SAMPLE_PLAN

    def test_reset_then_write_restores_original(self, tmp_path):
        plan_file = tmp_path / "IMPLEMENTATION_PLAN.md"
        plan_file.write_text(_SAMPLE_PLAN)
        state = parse_plan(plan_file)
        state.mark_complete(5)
        state.reset_uncommitted()
        state.write()
        assert plan_file.read_text() == _SAMPLE_PLAN
