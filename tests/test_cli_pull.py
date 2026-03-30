import pathlib
import yaml
from unittest.mock import patch
from click.testing import CliRunner

from agentic_stacks_cli import cli

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "registry"


@patch("agentic_stacks_cli.commands.pull.ensure_registry")
@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_by_name(mock_clone, mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "openstack-kolla",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once_with(
        "https://github.com/agentic-stacks/openstack-kolla",
        tmp_path / ".stacks" / "openstack-kolla",
    )


@patch("agentic_stacks_cli.commands.pull.ensure_registry")
@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_by_owner_name(mock_clone, mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "agentic-stacks/dell-hardware",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once_with(
        "https://github.com/agentic-stacks/dell-hardware",
        tmp_path / ".stacks" / "dell-hardware",
    )


@patch("agentic_stacks_cli.commands.pull.ensure_registry")
@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_resolves_from_formula(mock_clone, mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "openstack-kolla",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    # Should resolve from formula, not convention
    mock_clone.assert_called_once_with(
        "https://github.com/agentic-stacks/openstack-kolla",
        tmp_path / ".stacks" / "openstack-kolla",
    )


@patch("agentic_stacks_cli.commands.pull.ensure_registry")
@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_formula_not_found_falls_back(mock_clone, mock_ensure, tmp_path):
    """When formula doesn't exist, fall back to GitHub URL convention."""
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "someuser/unknown-stack",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once_with(
        "https://github.com/someuser/unknown-stack",
        tmp_path / ".stacks" / "unknown-stack",
    )


@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_creates_lock_entry(mock_clone, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    with patch("agentic_stacks_cli.commands.pull.ensure_registry") as mock_ensure:
        mock_ensure.return_value = FIXTURES
        runner.invoke(cli, [
            "pull", "agentic-stacks/openstack-kolla",
            "--dir", str(tmp_path), "--config", str(config_path),
        ])
    lock = yaml.safe_load((tmp_path / "stacks.lock").read_text())
    assert len(lock["stacks"]) == 1
    assert lock["stacks"][0]["name"] == "agentic-stacks/openstack-kolla"
    assert lock["stacks"][0]["repository"] == "https://github.com/agentic-stacks/openstack-kolla"


@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_from_lock(mock_clone, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    lock = {
        "stacks": [{
            "name": "agentic-stacks/openstack-kolla",
            "version": "latest",
            "repository": "https://github.com/agentic-stacks/openstack-kolla",
        }]
    }
    (tmp_path / "stacks.lock").write_text(yaml.dump(lock))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once()


def test_pull_no_lock_no_ref(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code != 0
