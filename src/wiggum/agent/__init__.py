"""Agent abstraction for delegating work to sub-agents."""

import dataclasses
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclasses.dataclass(frozen=True)
class AgentResult:
    """Result of an agent invocation."""

    stdout: str
    stderr: str
    exit_code: int

    @property
    def output(self) -> str:
        """Alias for stdout."""
        return self.stdout


@runtime_checkable
class AgentService(Protocol):
    """Protocol for invoking sub-agents."""

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Run an agent synchronously and return the result."""
        ...

    def run_background(self, *, prompt: str) -> object:
        """Run an agent in the background and return immediately."""
        ...


AgentPort = AgentService
