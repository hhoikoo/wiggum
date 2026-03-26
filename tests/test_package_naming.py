"""Tests for standardized package naming: no architecture jargon."""

from pathlib import Path

# -- git package: GitClient protocol in __init__.py --------------------------


def test_git_client_importable_from_git_package() -> None:
    """GitClient protocol should be importable from wiggum.git."""
    from wiggum.git import GitClient

    assert GitClient is not None


def test_git_client_is_runtime_checkable_protocol() -> None:
    """GitClient should be a runtime-checkable Protocol."""
    from wiggum.git import GitClient

    assert hasattr(GitClient, "__protocol_attrs__") or hasattr(
        GitClient, "_is_protocol"
    )


def test_git_client_has_expected_methods() -> None:
    """GitClient should expose all git operation methods."""
    from wiggum.git import GitClient

    expected = [
        "repo_root",
        "is_repo",
        "current_branch",
        "status",
        "diff",
        "diff_names",
        "log",
        "add",
        "stage_all",
        "commit",
    ]
    for method in expected:
        assert callable(getattr(GitClient, method, None)), f"GitClient missing {method}"


def test_git_dataclasses_in_package_init() -> None:
    """StatusEntry and LogEntry should be importable from wiggum.git."""
    from wiggum.git import LogEntry, StatusEntry

    assert StatusEntry is not None
    assert LogEntry is not None


def test_git_no_port_module() -> None:
    """port.py should not exist in the git package."""
    import wiggum.git as git_pkg

    pkg_dir = Path(git_pkg.__file__).parent
    assert not (pkg_dir / "port.py").exists(), "port.py should be removed"


# -- git package: SubprocessGit in shell.py ----------------------------------


def test_subprocess_git_importable() -> None:
    """SubprocessGit should be importable from wiggum.git.shell."""
    from wiggum.git.shell import SubprocessGit

    assert SubprocessGit is not None


def test_subprocess_git_satisfies_git_client(tmp_path: Path) -> None:
    """SubprocessGit should be recognized as a GitClient instance."""
    from wiggum.git import GitClient
    from wiggum.git.shell import SubprocessGit

    instance = SubprocessGit(repo_path=tmp_path)
    assert isinstance(instance, GitClient)


# -- agent package: AgentService protocol in __init__.py ---------------------


def test_agent_service_importable_from_agent_package() -> None:
    """AgentService protocol should be importable from wiggum.agent."""
    from wiggum.agent import AgentService

    assert AgentService is not None


def test_agent_service_is_runtime_checkable_protocol() -> None:
    """AgentService should be a runtime-checkable Protocol."""
    from wiggum.agent import AgentService

    assert hasattr(AgentService, "__protocol_attrs__") or hasattr(
        AgentService, "_is_protocol"
    )


def test_agent_service_has_expected_methods() -> None:
    """AgentService should expose run and run_background."""
    from wiggum.agent import AgentService

    assert callable(getattr(AgentService, "run", None))
    assert callable(getattr(AgentService, "run_background", None))


def test_agent_result_still_importable() -> None:
    """AgentResult should remain importable from wiggum.agent."""
    from wiggum.agent import AgentResult

    assert AgentResult is not None


# -- agent package: SubprocessAgent in shell.py ------------------------------


def test_subprocess_agent_importable() -> None:
    """SubprocessAgent should be importable from wiggum.agent.shell."""
    from wiggum.agent.shell import SubprocessAgent

    assert SubprocessAgent is not None


def test_subprocess_agent_satisfies_agent_service(tmp_path: Path) -> None:
    """SubprocessAgent should be recognized as an AgentService instance."""
    from wiggum.agent import AgentService
    from wiggum.agent.shell import SubprocessAgent

    instance = SubprocessAgent(work_dir=tmp_path)
    assert isinstance(instance, AgentService)
