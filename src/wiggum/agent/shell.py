"""Shell-based agent adapter invoking claude CLI as a subprocess."""

import subprocess
from typing import TYPE_CHECKING

from wiggum.agent import AgentResult

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


class SubprocessAgent:
    """AgentService implementation that delegates to the claude CLI."""

    def __init__(self, *, work_dir: Path) -> None:
        """Create an adapter targeting the given working directory."""
        self._work_dir = work_dir

    def run(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> AgentResult:
        """Run claude synchronously and return the result."""
        cmd = self._build_cmd(
            prompt=prompt, system_prompt=system_prompt, allowed_tools=allowed_tools
        )
        proc = subprocess.run(  # noqa: S603
            cmd, capture_output=True, text=True, check=False, cwd=self._work_dir
        )
        return AgentResult(
            stdout=proc.stdout, stderr=proc.stderr, exit_code=proc.returncode
        )

    def run_background(self, *, prompt: str) -> subprocess.Popen[str]:
        """Start claude in the background and return immediately."""
        cmd = self._build_cmd(prompt=prompt)
        return subprocess.Popen(  # noqa: S603
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self._work_dir,
        )

    def _build_cmd(
        self,
        *,
        prompt: str,
        system_prompt: str | None = None,
        allowed_tools: Sequence[str] | None = None,
    ) -> list[str]:
        cmd = ["claude", "-p", prompt]
        if system_prompt is not None:
            cmd.extend(["--system-prompt", system_prompt])
        if allowed_tools is not None:
            cmd.extend(["--tools", ",".join(allowed_tools)])
        return cmd


ShellAgentAdapter = SubprocessAgent
