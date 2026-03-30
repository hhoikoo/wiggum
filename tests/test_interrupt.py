"""Tests for the interrupt module -- SIGINT handler."""

import signal
import subprocess
from unittest.mock import MagicMock

import pytest

from wiggum.interrupt import (
    _handle_sigint,
    register_handler,
    set_active_plan,
    set_active_process,
)
from wiggum.plan import parse_plan


@pytest.fixture(autouse=True)
def _restore_signal_and_state():
    """Save/restore SIGINT handler and clear module state around each test."""
    old_handler = signal.getsignal(signal.SIGINT)
    yield
    signal.signal(signal.SIGINT, old_handler)
    set_active_process(None)
    set_active_plan(None)


class TestRegisterHandler:
    def test_installs_sigint_handler(self):
        register_handler()
        assert signal.getsignal(signal.SIGINT) is _handle_sigint


class TestSetters:
    def test_set_active_process(self):
        import wiggum.interrupt as mod

        proc = MagicMock(spec=subprocess.Popen)
        set_active_process(proc)
        assert mod._active_proc is proc

    def test_clear_active_process(self):
        import wiggum.interrupt as mod

        set_active_process(MagicMock(spec=subprocess.Popen))
        set_active_process(None)
        assert mod._active_proc is None

    def test_set_active_plan(self, tmp_path):
        import wiggum.interrupt as mod

        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("- [ ] task\n")
        state = parse_plan(plan_path)
        set_active_plan(state)
        assert mod._active_plan is state

    def test_clear_active_plan(self, tmp_path):
        import wiggum.interrupt as mod

        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("- [ ] task\n")
        set_active_plan(parse_plan(plan_path))
        set_active_plan(None)
        assert mod._active_plan is None


class TestHandleSigint:
    def test_exits_with_code_130(self):
        with pytest.raises(SystemExit) as exc_info:
            _handle_sigint(signal.SIGINT, None)
        assert exc_info.value.code == 130

    def test_sets_sig_ign_to_prevent_reentry(self):
        with pytest.raises(SystemExit):
            _handle_sigint(signal.SIGINT, None)
        assert signal.getsignal(signal.SIGINT) == signal.SIG_IGN

    def test_terminates_active_process(self):
        proc = MagicMock(spec=subprocess.Popen)
        set_active_process(proc)
        with pytest.raises(SystemExit):
            _handle_sigint(signal.SIGINT, None)
        proc.terminate.assert_called_once()
        proc.wait.assert_called_once_with(timeout=5)

    def test_kills_process_on_timeout(self):
        proc = MagicMock(spec=subprocess.Popen)
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=5)
        set_active_process(proc)
        with pytest.raises(SystemExit):
            _handle_sigint(signal.SIGINT, None)
        proc.terminate.assert_called_once()
        proc.kill.assert_called_once()

    def test_does_not_kill_when_terminate_succeeds(self):
        proc = MagicMock(spec=subprocess.Popen)
        set_active_process(proc)
        with pytest.raises(SystemExit):
            _handle_sigint(signal.SIGINT, None)
        proc.kill.assert_not_called()

    def test_resets_uncommitted_marks(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("- [ ] first task\n- [ ] second task\n")
        state = parse_plan(plan_path)
        state.mark_complete(1)
        set_active_plan(state)
        with pytest.raises(SystemExit):
            _handle_sigint(signal.SIGINT, None)
        text = plan_path.read_text()
        assert "- [ ] first task" in text
        assert "- [ ] second task" in text

    def test_preserves_previously_committed_marks(self, tmp_path):
        plan_path = tmp_path / "PLAN.md"
        plan_path.write_text("- [x] already done\n- [ ] in progress\n")
        state = parse_plan(plan_path)
        state.mark_complete(2)
        set_active_plan(state)
        with pytest.raises(SystemExit):
            _handle_sigint(signal.SIGINT, None)
        text = plan_path.read_text()
        assert "- [x] already done" in text
        assert "- [ ] in progress" in text

    def test_handles_no_active_state(self):
        with pytest.raises(SystemExit) as exc_info:
            _handle_sigint(signal.SIGINT, None)
        assert exc_info.value.code == 130
