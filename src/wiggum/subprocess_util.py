"""Subprocess wrapper for invoking claude CLI."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wiggum.config import ModelConfig


@dataclass(frozen=True, slots=True)
class InvokeResult:
    """Structured result from a claude CLI invocation."""

    stdout: str
    exit_code: int


_CLAUDE_BIN = "claude"


def invoke_claude(
    prompt: str,
    *,
    model: ModelConfig | None = None,
) -> InvokeResult:
    """Invoke ``claude -p --dangerously-skip-permissions`` with *prompt* on stdin.

    Captures stdout; stderr streams directly to the terminal.
    """
    cmd: list[str] = [_CLAUDE_BIN, "-p", "--dangerously-skip-permissions"]

    if model and model.name:
        cmd.extend(["--model", model.name])
    if model:
        cmd.extend(model.flags)

    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
    )
    stdout, _ = proc.communicate(input=prompt)
    return InvokeResult(stdout=stdout, exit_code=proc.returncode)
