"""Tests for build_green_prompt: plan inclusion, round-1 items, and fix-round failures."""

from wiggum.plan import PlanItem

_PLAN_TEXT = """\
# My Plan

### Auth
- [x] Add login endpoint
- [ ] Add logout endpoint

### Database
- [ ] Create users table
"""

_ROUND1_ITEMS = [
    PlanItem(description="Add logout endpoint"),
    PlanItem(description="Create users table"),
]

_FAILURE_DESCRIPTIONS = [
    "ruff: unused import `os` in src/wiggum/auth.py:3",
    "FAILED tests/test_auth.py::test_logout - AttributeError: missing 'logout' method",
]


class TestBuildGreenPromptImport:
    """build_green_prompt is importable from wiggum.prompts."""

    def test_importable(self) -> None:
        from wiggum.prompts import build_green_prompt

        assert callable(build_green_prompt)


class TestBuildGreenPromptPlanInclusion:
    """The green prompt always includes the existing plan text."""

    def test_plan_text_present_in_round1(self) -> None:
        from wiggum.prompts import build_green_prompt

        prompt = build_green_prompt(
            plan_text=_PLAN_TEXT,
            tasks=[item.description for item in _ROUND1_ITEMS],
        )
        assert _PLAN_TEXT in prompt

    def test_plan_text_present_in_fix_round(self) -> None:
        from wiggum.prompts import build_green_prompt

        prompt = build_green_prompt(
            plan_text=_PLAN_TEXT,
            tasks=_FAILURE_DESCRIPTIONS,
            is_fix_round=True,
        )
        assert _PLAN_TEXT in prompt


class TestBuildGreenPromptRound1:
    """Round 1 gets plan items as tasks."""

    def test_each_item_description_appears(self) -> None:
        from wiggum.prompts import build_green_prompt

        prompt = build_green_prompt(
            plan_text=_PLAN_TEXT,
            tasks=[item.description for item in _ROUND1_ITEMS],
        )
        for item in _ROUND1_ITEMS:
            assert item.description in prompt

    def test_is_not_fix_round_by_default(self) -> None:
        from wiggum.prompts import build_green_prompt

        prompt = build_green_prompt(
            plan_text=_PLAN_TEXT,
            tasks=[item.description for item in _ROUND1_ITEMS],
        )
        # Round 1 prompt should not contain fix-round framing
        prompt_lower = prompt.lower()
        assert "fix" not in prompt_lower or "failure" not in prompt_lower


class TestBuildGreenPromptFixRound:
    """Fix rounds get triaged failure descriptions as tasks."""

    def test_each_failure_description_appears(self) -> None:
        from wiggum.prompts import build_green_prompt

        prompt = build_green_prompt(
            plan_text=_PLAN_TEXT,
            tasks=_FAILURE_DESCRIPTIONS,
            is_fix_round=True,
        )
        for failure in _FAILURE_DESCRIPTIONS:
            assert failure in prompt

    def test_fix_round_differs_from_round1(self) -> None:
        from wiggum.prompts import build_green_prompt

        tasks = ["Add logout endpoint"]
        round1 = build_green_prompt(plan_text=_PLAN_TEXT, tasks=tasks)
        fix = build_green_prompt(plan_text=_PLAN_TEXT, tasks=tasks, is_fix_round=True)
        assert round1 != fix


class TestBuildGreenPromptReturnType:
    """build_green_prompt returns a non-empty string."""

    def test_returns_string(self) -> None:
        from wiggum.prompts import build_green_prompt

        result = build_green_prompt(
            plan_text=_PLAN_TEXT,
            tasks=["Add logout endpoint"],
        )
        assert isinstance(result, str)

    def test_returns_nonempty(self) -> None:
        from wiggum.prompts import build_green_prompt

        result = build_green_prompt(
            plan_text=_PLAN_TEXT,
            tasks=["Add logout endpoint"],
        )
        assert len(result.strip()) > 0
