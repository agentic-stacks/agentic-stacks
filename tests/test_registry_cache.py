import pathlib
import subprocess
from unittest.mock import patch

from agentic_stacks_cli.registry_repo import ensure_registry, registry_cache_path


def test_registry_cache_path():
    path = registry_cache_path()
    assert str(path).endswith("agentic-stacks/registry")


def test_registry_cache_path_custom():
    path = registry_cache_path(config_dir=pathlib.Path("/tmp/test"))
    assert path == pathlib.Path("/tmp/test/registry")


@patch("agentic_stacks_cli.registry_repo.subprocess.run")
def test_ensure_registry_clones_when_missing(mock_run, tmp_path):
    cache_dir = tmp_path / "registry"
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

    ensure_registry(
        repo_url="https://github.com/agentic-stacks/registry",
        cache_dir=cache_dir,
    )

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert args[0] == "git"
    assert args[1] == "clone"
    assert "https://github.com/agentic-stacks/registry" in args


@patch("agentic_stacks_cli.registry_repo.subprocess.run")
def test_ensure_registry_updates_when_exists(mock_run, tmp_path):
    cache_dir = tmp_path / "registry"
    cache_dir.mkdir()
    (cache_dir / ".git").mkdir()
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

    ensure_registry(
        repo_url="https://github.com/agentic-stacks/registry",
        cache_dir=cache_dir,
    )

    # Should fetch + reset, not clone
    assert mock_run.call_count == 2
    first_args = mock_run.call_args_list[0][0][0]
    assert "fetch" in first_args
    second_args = mock_run.call_args_list[1][0][0]
    assert "reset" in second_args
