"""Tests for select_items() in wiggum.priority."""

from __future__ import annotations

from typing import TYPE_CHECKING

from wiggum.agent import AgentPort, AgentResult
from wiggum.plan import PlanItem
from wiggum.priority import select_items

if TYPE_CHECKING:
    from collections.abc import Sequence

# -- Fake agent for testing ----------------------------------------------------

_DEFAULT_ITEMS: Sequence[PlanItem] = (
    PlanItem(description="Set up CI pipeline"),
    PlanItem(description="Add database schema"),
    PlanItem(description="Write API endpoint"),
    PlanItem(description="Create frontend form"),
)


class FakeAgent:
    """Agent that returns a canned response listing items in a given order."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def run(self, *, prompt: str, system_prompt: str | None = None) -> AgentResult:
        """Record the prompt and return the canned response."""
        self.prompts.append(prompt)
        return AgentResult(stdout=self.response, stderr="", exit_code=0)

    def run_background(self, *, prompt: str) -> object:
        """Not used in select_items tests."""
        raise NotImplementedError


def _make_response(*descriptions: str) -> str:
    """Build a numbered-list response like the agent would produce."""
    return "\n".join(f"{i + 1}. {d}" for i, d in enumerate(descriptions))


# -- Return value shape --------------------------------------------------------


class TestSelectItemsReturnShape:
    """Tests for the shape and type of select_items return value."""

    def test_returns_list(self) -> None:
        agent = FakeAgent(_make_response("Set up CI pipeline"))
        result = select_items(items=_DEFAULT_ITEMS, agent=agent, count=1)
        assert isinstance(result, list)

    def test_elements_are_plan_items(self) -> None:
        agent = FakeAgent(_make_response("Set up CI pipeline"))
        result = select_items(items=_DEFAULT_ITEMS, agent=agent, count=1)
        assert all(isinstance(item, PlanItem) for item in result)


# -- Count behavior ------------------------------------------------------------


class TestSelectItemsCount:
    """Tests for how count limits the returned items."""

    def test_returns_at_most_count_items(self) -> None:
        agent = FakeAgent(_make_response("Set up CI pipeline", "Add database schema"))
        result = select_items(items=_DEFAULT_ITEMS, agent=agent, count=2)
        assert len(result) <= 2

    def test_fewer_items_than_count_returns_all(self) -> None:
        two_items = _DEFAULT_ITEMS[:2]
        agent = FakeAgent(_make_response("Set up CI pipeline", "Add database schema"))
        result = select_items(items=two_items, agent=agent, count=5)
        assert len(result) == 2

    def test_count_one_returns_single_item(self) -> None:
        agent = FakeAgent(_make_response("Add database schema"))
        result = select_items(items=_DEFAULT_ITEMS, agent=agent, count=1)
        assert len(result) == 1


# -- Empty input ---------------------------------------------------------------


class TestSelectItemsEmptyInput:
    """Tests for select_items with no input items."""

    def test_empty_items_returns_empty_list(self) -> None:
        agent = FakeAgent("")
        result = select_items(items=[], agent=agent, count=3)
        assert result == []

    def test_empty_items_does_not_call_agent(self) -> None:
        agent = FakeAgent("")
        select_items(items=[], agent=agent, count=3)
        assert len(agent.prompts) == 0


# -- Agent interaction ---------------------------------------------------------


class TestSelectItemsAgentInteraction:
    """Tests for how select_items uses the agent."""

    def test_calls_agent_run(self) -> None:
        agent = FakeAgent(_make_response("Set up CI pipeline"))
        select_items(items=_DEFAULT_ITEMS, agent=agent, count=1)
        assert len(agent.prompts) == 1

    def test_prompt_contains_item_descriptions(self) -> None:
        agent = FakeAgent(_make_response("Set up CI pipeline"))
        select_items(items=_DEFAULT_ITEMS, agent=agent, count=1)
        prompt = agent.prompts[0]
        for item in _DEFAULT_ITEMS:
            assert item.description in prompt


# -- Ordering ------------------------------------------------------------------


class TestSelectItemsOrdering:
    """Tests for dependency-order selection from agent response."""

    def test_respects_agent_ordering(self) -> None:
        agent = FakeAgent(_make_response("Add database schema", "Set up CI pipeline"))
        result = select_items(items=_DEFAULT_ITEMS, agent=agent, count=2)
        assert result[0].description == "Add database schema"
        assert result[1].description == "Set up CI pipeline"

    def test_returns_original_plan_items(self) -> None:
        agent = FakeAgent(_make_response("Write API endpoint"))
        result = select_items(items=_DEFAULT_ITEMS, agent=agent, count=1)
        assert result[0] is _DEFAULT_ITEMS[2]


# -- Protocol conformance -----------------------------------------------------


class TestSelectItemsProtocol:
    """Tests that FakeAgent satisfies AgentPort protocol."""

    def test_fake_agent_is_agent_port(self) -> None:
        agent = FakeAgent("")
        assert isinstance(agent, AgentPort)
