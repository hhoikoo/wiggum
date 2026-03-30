"""SIGINT handler with mark reset and subprocess termination."""

import signal
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType
    from typing import NoReturn

    from wiggum.plan import PlanState

_SIGINT_EXIT_CODE = 130
_TERMINATE_TIMEOUT_SECONDS = 5

_active_proc: subprocess.Popen[str] | None = None
_active_plan: PlanState | None = None


def set_active_process(proc: subprocess.Popen[str] | None) -> None:
    """Set or clear the active subprocess for SIGINT termination."""
    global _active_proc  # noqa: PLW0603
    _active_proc = proc


def set_active_plan(plan: PlanState | None) -> None:
    """Set or clear the active plan state for SIGINT mark reset."""
    global _active_plan  # noqa: PLW0603
    _active_plan = plan


def _handle_sigint(_signum: int, _frame: FrameType | None) -> NoReturn:
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    if _active_proc is not None:
        _active_proc.terminate()
        try:
            _active_proc.wait(timeout=_TERMINATE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            _active_proc.kill()

    if _active_plan is not None:
        _active_plan.reset_uncommitted()
        _active_plan.write()

    sys.exit(_SIGINT_EXIT_CODE)


def register_handler() -> None:
    """Register the SIGINT handler for graceful shutdown."""
    signal.signal(signal.SIGINT, _handle_sigint)
