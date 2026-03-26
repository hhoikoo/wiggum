"""Tests for run_checks() in wiggum.checks."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from wiggum.checks import CheckResult, run_checks

_REPO_PATH = Path("/fake/repo")


def _completed(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _side_effect(
    *, lint_rc: int = 0, test_rc: int = 0, lint_stdout: str = "", test_stdout: str = ""
):
    def _run(cmd, **_kwargs):
        if "ruff" in cmd:
            return _completed(returncode=lint_rc, stdout=lint_stdout)
        if "pytest" in cmd:
            return _completed(returncode=test_rc, stdout=test_stdout)
        msg = f"Unexpected command: {cmd}"
        raise ValueError(msg)

    return _run


class TestCheckResultPassedProperty:
    def test_true_when_both_pass(self):
        result = CheckResult(
            lint_passed=True, test_passed=True, lint_output="", test_output=""
        )
        assert result.passed is True

    def test_false_when_lint_fails(self):
        result = CheckResult(
            lint_passed=False, test_passed=True, lint_output="", test_output=""
        )
        assert result.passed is False

    def test_false_when_test_fails(self):
        result = CheckResult(
            lint_passed=True, test_passed=False, lint_output="", test_output=""
        )
        assert result.passed is False

    def test_false_when_both_fail(self):
        result = CheckResult(
            lint_passed=False, test_passed=False, lint_output="", test_output=""
        )
        assert result.passed is False


class TestRunChecksReturnType:
    @patch("wiggum.checks.subprocess.run")
    def test_returns_check_result(self, mock_run):
        mock_run.return_value = _completed()
        result = run_checks(repo_path=_REPO_PATH)
        assert isinstance(result, CheckResult)


class TestRunChecksPassFail:
    @patch("wiggum.checks.subprocess.run")
    def test_both_passing(self, mock_run):
        mock_run.side_effect = _side_effect(lint_rc=0, test_rc=0)
        result = run_checks(repo_path=_REPO_PATH)
        assert result.lint_passed is True
        assert result.test_passed is True
        assert result.passed is True

    @patch("wiggum.checks.subprocess.run")
    def test_lint_failure(self, mock_run):
        mock_run.side_effect = _side_effect(lint_rc=1)
        result = run_checks(repo_path=_REPO_PATH)
        assert result.lint_passed is False
        assert result.passed is False

    @patch("wiggum.checks.subprocess.run")
    def test_pytest_failure(self, mock_run):
        mock_run.side_effect = _side_effect(test_rc=1)
        result = run_checks(repo_path=_REPO_PATH)
        assert result.test_passed is False
        assert result.passed is False

    @patch("wiggum.checks.subprocess.run")
    def test_pytest_exit_5_no_tests_collected_is_pass(self, mock_run):
        mock_run.side_effect = _side_effect(test_rc=5)
        result = run_checks(repo_path=_REPO_PATH)
        assert result.test_passed is True
        assert result.passed is True

    @patch("wiggum.checks.subprocess.run")
    def test_both_failing(self, mock_run):
        mock_run.side_effect = _side_effect(lint_rc=1, test_rc=1)
        result = run_checks(repo_path=_REPO_PATH)
        assert result.lint_passed is False
        assert result.test_passed is False
        assert result.passed is False


class TestRunChecksSubprocessCalls:
    @patch("wiggum.checks.subprocess.run")
    def test_invokes_ruff_check(self, mock_run):
        mock_run.side_effect = _side_effect()
        run_checks(repo_path=_REPO_PATH)
        ruff_calls = [c for c in mock_run.call_args_list if "ruff" in c.args[0]]
        assert len(ruff_calls) == 1

    @patch("wiggum.checks.subprocess.run")
    def test_invokes_pytest(self, mock_run):
        mock_run.side_effect = _side_effect()
        run_checks(repo_path=_REPO_PATH)
        pytest_calls = [c for c in mock_run.call_args_list if "pytest" in c.args[0]]
        assert len(pytest_calls) == 1

    @patch("wiggum.checks.subprocess.run")
    def test_runs_in_repo_directory(self, mock_run):
        mock_run.side_effect = _side_effect()
        run_checks(repo_path=_REPO_PATH)
        for c in mock_run.call_args_list:
            assert c.kwargs.get("cwd") == _REPO_PATH


class TestRunChecksOutputCapture:
    @patch("wiggum.checks.subprocess.run")
    def test_captures_lint_output(self, mock_run):
        mock_run.side_effect = _side_effect(lint_stdout="all good")
        result = run_checks(repo_path=_REPO_PATH)
        assert "all good" in result.lint_output

    @patch("wiggum.checks.subprocess.run")
    def test_captures_test_output(self, mock_run):
        mock_run.side_effect = _side_effect(test_stdout="3 passed")
        result = run_checks(repo_path=_REPO_PATH)
        assert "3 passed" in result.test_output


# -- run_autofix ---------------------------------------------------------------


class TestRunAutofixImport:
    """run_autofix is importable from wiggum.checks."""

    def test_importable(self):
        from wiggum.checks import run_autofix

        assert callable(run_autofix)


class TestRunAutofixUsesFixFlag:
    """run_autofix invokes ruff with --fix."""

    @patch("wiggum.checks.subprocess.run")
    def test_command_includes_fix_flag(self, mock_run):
        from wiggum.checks import run_autofix

        mock_run.return_value = _completed()
        run_autofix(repo_path=_REPO_PATH)
        ruff_calls = [c for c in mock_run.call_args_list if "ruff" in c.args[0]]
        assert len(ruff_calls) == 1
        assert "--fix" in ruff_calls[0].args[0]


class TestRunAutofixNoUnsafeFixes:
    """run_autofix must NOT use --unsafe-fixes."""

    @patch("wiggum.checks.subprocess.run")
    def test_command_excludes_unsafe_fixes(self, mock_run):
        from wiggum.checks import run_autofix

        mock_run.return_value = _completed()
        run_autofix(repo_path=_REPO_PATH)
        ruff_calls = [c for c in mock_run.call_args_list if "ruff" in c.args[0]]
        assert len(ruff_calls) == 1
        assert "--unsafe-fixes" not in ruff_calls[0].args[0]


class TestRunAutofixRunsInRepoDir:
    """run_autofix runs in the specified repo directory."""

    @patch("wiggum.checks.subprocess.run")
    def test_cwd_is_repo_path(self, mock_run):
        from wiggum.checks import run_autofix

        mock_run.return_value = _completed()
        run_autofix(repo_path=_REPO_PATH)
        for c in mock_run.call_args_list:
            assert c.kwargs.get("cwd") == _REPO_PATH


class TestRunAutofixReturnType:
    """run_autofix returns an AutofixResult."""

    @patch("wiggum.checks.subprocess.run")
    def test_returns_autofix_result(self, mock_run):
        from wiggum.checks import AutofixResult, run_autofix

        mock_run.return_value = _completed()
        result = run_autofix(repo_path=_REPO_PATH)
        assert isinstance(result, AutofixResult)


class TestAutofixResultFields:
    """AutofixResult exposes success status and output."""

    @patch("wiggum.checks.subprocess.run")
    def test_success_when_returncode_zero(self, mock_run):
        from wiggum.checks import run_autofix

        mock_run.return_value = _completed(returncode=0, stdout="All checks passed")
        result = run_autofix(repo_path=_REPO_PATH)
        assert result.success is True

    @patch("wiggum.checks.subprocess.run")
    def test_failure_when_returncode_nonzero(self, mock_run):
        from wiggum.checks import run_autofix

        mock_run.return_value = _completed(returncode=1, stdout="Found 3 errors")
        result = run_autofix(repo_path=_REPO_PATH)
        assert result.success is False

    @patch("wiggum.checks.subprocess.run")
    def test_captures_output(self, mock_run):
        from wiggum.checks import run_autofix

        mock_run.return_value = _completed(stdout="Fixed 2 errors")
        result = run_autofix(repo_path=_REPO_PATH)
        assert result.output == "Fixed 2 errors"


class TestRunAutofixTargetsDirs:
    """run_autofix targets src/ and tests/ directories."""

    @patch("wiggum.checks.subprocess.run")
    def test_command_includes_src_and_tests(self, mock_run):
        from wiggum.checks import run_autofix

        mock_run.return_value = _completed()
        run_autofix(repo_path=_REPO_PATH)
        ruff_calls = [c for c in mock_run.call_args_list if "ruff" in c.args[0]]
        cmd = ruff_calls[0].args[0]
        assert "src/" in cmd
        assert "tests/" in cmd
