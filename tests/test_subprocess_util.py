from unittest.mock import MagicMock, patch

from wiggum.config import ModelConfig
from wiggum.subprocess_util import InvokeResult, invoke_claude


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
