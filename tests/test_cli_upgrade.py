import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli
from agentic_stacks_cli.lock import write_lock


@patch("agentic_stacks_cli.commands.upgrade.pull_stack")
@patch("agentic_stacks_cli.commands.upgrade.RegistryClient")
def test_upgrade_finds_newer_version(mock_client_cls, mock_pull, tmp_path):
    lock_path = tmp_path / "stacks.lock"
    write_lock({"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.2.0",
         "digest": "sha256:old", "registry": "ghcr.io/agentic-stacks/openstack:1.2.0"}
    ]}, lock_path)
    mock_client = MagicMock()
    mock_client.get_stack.return_value = {
        "name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0", "deprecations": [],
    }
    mock_client_cls.return_value = mock_client
    mock_pull.return_value = "sha256:new123"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry": "ghcr.io", "api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["upgrade", "openstack", "--dir", str(tmp_path), "--config", str(config_path)])
    assert result.exit_code == 0
    assert "1.3.0" in result.output
    lock = yaml.safe_load(lock_path.read_text())
    assert lock["stacks"][0]["version"] == "1.3.0"


@patch("agentic_stacks_cli.commands.upgrade.RegistryClient")
def test_upgrade_already_latest(mock_client_cls, tmp_path):
    lock_path = tmp_path / "stacks.lock"
    write_lock({"stacks": [
        {"name": "agentic-stacks/openstack", "version": "1.3.0",
         "digest": "sha256:abc", "registry": "ghcr.io/agentic-stacks/openstack:1.3.0"}
    ]}, lock_path)
    mock_client = MagicMock()
    mock_client.get_stack.return_value = {"name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0"}
    mock_client_cls.return_value = mock_client
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["upgrade", "openstack", "--dir", str(tmp_path), "--config", str(config_path)])
    assert result.exit_code == 0
    assert "already" in result.output.lower() or "latest" in result.output.lower() or "up to date" in result.output.lower()


def test_upgrade_not_in_lock(tmp_path):
    write_lock({"stacks": []}, tmp_path / "stacks.lock")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["upgrade", "openstack", "--dir", str(tmp_path), "--config", str(config_path)])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "lock" in result.output.lower()
