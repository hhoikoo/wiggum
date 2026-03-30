from unittest.mock import MagicMock, patch

import pytest

import wiggum.interrupt as interrupt_mod
from wiggum.config import ModelConfig
from wiggum.interrupt import set_active_process
from wiggum.subprocess_util import InvokeResult, invoke_claude


@pytest.fixture(autouse=True)
def _clear_active_process():
    yield
    set_active_process(None)


class TestInvokeResult:
    def test_fields(self):
        result = InvokeResult(stdout="hello", exit_code=0)
        assert result.stdout == "hello"
        assert result.exit_code == 0


class TestInvokeClaude:
    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_basic_invocation(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        proc.communicate.return_value = ("output text", None)
        proc.returncode = 0
        mock_popen_cls.return_value = proc

        result = invoke_claude("my prompt")

        mock_popen_cls.assert_called_once()
        args, kwargs = mock_popen_cls.call_args
        cmd = args[0]
        assert cmd == ["claude", "-p", "--dangerously-skip-permissions"]
        assert kwargs["stdin"] is not None
        assert kwargs["stdout"] is not None
        assert kwargs["stderr"] is None
        assert kwargs["text"] is True

        proc.communicate.assert_called_once_with(input="my prompt")
        assert result == InvokeResult(stdout="output text", exit_code=0)

    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_passes_model_name(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        proc.communicate.return_value = ("", None)
        proc.returncode = 0
        mock_popen_cls.return_value = proc

        invoke_claude("prompt", model=ModelConfig(name="opus"))

        cmd = mock_popen_cls.call_args[0][0]
        assert "--model" in cmd
        assert cmd[cmd.index("--model") + 1] == "opus"

    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_skips_model_flag_when_name_empty(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        proc.communicate.return_value = ("", None)
        proc.returncode = 0
        mock_popen_cls.return_value = proc

        invoke_claude("prompt", model=ModelConfig(name=""))

        cmd = mock_popen_cls.call_args[0][0]
        assert "--model" not in cmd

    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_passes_extra_flags(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        proc.communicate.return_value = ("", None)
        proc.returncode = 0
        mock_popen_cls.return_value = proc

        invoke_claude(
            "prompt",
            model=ModelConfig(name="sonnet", flags=["--max-turns", "50"]),
        )

        cmd = mock_popen_cls.call_args[0][0]
        assert cmd[-2:] == ["--max-turns", "50"]

    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_no_model_config(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        proc.communicate.return_value = ("", None)
        proc.returncode = 0
        mock_popen_cls.return_value = proc

        invoke_claude("prompt", model=None)

        cmd = mock_popen_cls.call_args[0][0]
        assert cmd == ["claude", "-p", "--dangerously-skip-permissions"]

    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_nonzero_exit_code(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        proc.communicate.return_value = ("error output", None)
        proc.returncode = 1
        mock_popen_cls.return_value = proc

        result = invoke_claude("prompt")

        assert result.exit_code == 1
        assert result.stdout == "error output"

    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_captures_stdout(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        proc.communicate.return_value = ("line1\nline2\nline3", None)
        proc.returncode = 0
        mock_popen_cls.return_value = proc

        result = invoke_claude("prompt")

        assert result.stdout == "line1\nline2\nline3"

    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_sets_active_process_before_communicate(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        active_at_communicate: list[object] = []

        def capture_state(*args: object, **kwargs: object) -> tuple[str, None]:
            active_at_communicate.append(interrupt_mod._active_proc)
            return ("output", None)

        proc.communicate.side_effect = capture_state
        proc.returncode = 0
        mock_popen_cls.return_value = proc

        invoke_claude("prompt")

        assert len(active_at_communicate) == 1
        assert active_at_communicate[0] is proc

    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_clears_active_process_after_success(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        proc.communicate.return_value = ("output", None)
        proc.returncode = 0
        mock_popen_cls.return_value = proc

        invoke_claude("prompt")

        assert interrupt_mod._active_proc is None

    @patch("wiggum.subprocess_util.subprocess.Popen")
    def test_clears_active_process_after_exception(self, mock_popen_cls: MagicMock):
        proc = MagicMock()
        proc.communicate.side_effect = RuntimeError("subprocess error")
        mock_popen_cls.return_value = proc

        with pytest.raises(RuntimeError):
            invoke_claude("prompt")

        assert interrupt_mod._active_proc is None
