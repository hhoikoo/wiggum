"""Quality checks for the inner loop."""

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

_PYTEST_EXIT_NO_TESTS_COLLECTED = 5


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Result of running lint and test checks."""

    lint_passed: bool
    test_passed: bool
    lint_output: str
    test_output: str

    @property
    def passed(self) -> bool:
        """True when all checks passed."""
        return self.lint_passed and self.test_passed


@dataclass(frozen=True, slots=True)
class AutofixResult:
    """Result of running ruff autofix."""

    success: bool
    output: str


def run_autofix(*, repo_path: Path) -> AutofixResult:
    """Run ruff check --fix on src/ and tests/."""
    result = subprocess.run(
        ["uv", "run", "ruff", "check", "--fix", "src/", "tests/"],  # noqa: S607
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    return AutofixResult(success=result.returncode == 0, output=result.stdout)


def run_checks(*, repo_path: Path) -> CheckResult:
    """Run ruff check and pytest, returning a combined result."""
    lint = subprocess.run(
        ["uv", "run", "ruff", "check", "src/", "tests/"],  # noqa: S607
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    test = subprocess.run(
        ["uv", "run", "pytest"],  # noqa: S607
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    return CheckResult(
        lint_passed=lint.returncode == 0,
        test_passed=test.returncode in (0, _PYTEST_EXIT_NO_TESTS_COLLECTED),
        lint_output=lint.stdout,
        test_output=test.stdout,
    )
