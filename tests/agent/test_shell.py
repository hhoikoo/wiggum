from __future__ import annotations

import subprocess
from unittest.mock import patch

from wiggum.agent import AgentResult
from wiggum.agent.shell import ShellAgentAdapter


class TestShellAgentAdapterRun:
    def test_invokes_claude_with_prompt(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude", "-p", "hello"],
                returncode=0,
                stdout="response text",
                stderr="",
            )
            adapter.run(prompt="hello")

        mock_run.assert_called_once()
        args = mock_run.call_args
        cmd = args[0][0] if args[0] else args[1]["args"]
        assert "claude" in cmd
        assert "-p" in cmd
        assert "hello" in cmd

    def test_returns_agent_result(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude", "-p", "test"],
                returncode=0,
                stdout="output text",
                stderr="",
            )
            result = adapter.run(prompt="test")

        assert isinstance(result, AgentResult)

    def test_captures_stdout(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude", "-p", "test"],
                returncode=0,
                stdout="captured output",
                stderr="",
            )
            result = adapter.run(prompt="test")

        assert result.stdout == "captured output"

    def test_captures_stderr(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude", "-p", "test"],
                returncode=0,
                stdout="",
                stderr="warning message",
            )
            result = adapter.run(prompt="test")

        assert result.stderr == "warning message"

    def test_captures_exit_code(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude", "-p", "test"],
                returncode=1,
                stdout="",
                stderr="error",
            )
            result = adapter.run(prompt="test")

        assert result.exit_code == 1

    def test_output_property_aliases_stdout(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude", "-p", "test"],
                returncode=0,
                stdout="alias check",
                stderr="",
            )
            result = adapter.run(prompt="test")

        assert result.output == "alias check"
        assert result.output == result.stdout

    def test_sets_cwd_to_work_dir(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude", "-p", "test"],
                returncode=0,
                stdout="",
                stderr="",
            )
            adapter.run(prompt="test")

        call_kwargs = mock_run.call_args
        # cwd should be passed as keyword arg or positional
        assert call_kwargs.kwargs.get("cwd") == tmp_path or (
            len(call_kwargs.args) > 1 and call_kwargs.args[1] == tmp_path
        )

    def test_passes_system_prompt(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["claude"],
                returncode=0,
                stdout="",
                stderr="",
            )
            adapter.run(prompt="do stuff", system_prompt="you are helpful")

        cmd = mock_run.call_args[0][0]
        assert "--system-prompt" in cmd or "-s" in cmd


class TestShellAgentAdapterRunBackground:
    def test_returns_immediately(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 12345
            _result = adapter.run_background(prompt="long task")

        mock_popen.assert_called_once()

    def test_invokes_claude_with_prompt(self, tmp_path):
        adapter = ShellAgentAdapter(work_dir=tmp_path)
        with patch("wiggum.agent.shell.subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 12345
            adapter.run_background(prompt="background task")

        cmd = mock_popen.call_args[0][0]
        assert "claude" in cmd
        assert "-p" in cmd
        assert "background task" in cmd
