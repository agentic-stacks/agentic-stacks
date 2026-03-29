import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from agentic_stacks_cli import cli


@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_by_name(mock_clone, tmp_path):
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


@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_by_namespace_name(mock_clone, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, [
        "pull", "myorg/my-stack",
        "--dir", str(tmp_path), "--config", str(config_path),
    ])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once_with(
        "https://github.com/myorg/my-stack",
        tmp_path / ".stacks" / "my-stack",
    )


@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_pull_creates_lock_entry(mock_clone, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
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
