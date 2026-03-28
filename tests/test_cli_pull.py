import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli


@patch("agentic_stacks_cli.commands.pull.pull_stack")
@patch("agentic_stacks_cli.commands.pull.RegistryClient")
def test_pull_by_name_and_version(mock_client_cls, mock_pull, tmp_path):
    mock_client = MagicMock()
    mock_client.get_stack.return_value = {
        "name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0"
    }
    mock_client_cls.return_value = mock_client
    mock_pull.return_value = "sha256:abc123"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry": "ghcr.io", "api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["pull", "agentic-stacks/openstack@1.3.0",
                                  "--dir", str(tmp_path), "--config", str(config_path)])
    assert result.exit_code == 0
    mock_pull.assert_called_once()


@patch("agentic_stacks_cli.commands.pull.pull_stack")
@patch("agentic_stacks_cli.commands.pull.RegistryClient")
def test_pull_creates_lock_entry(mock_client_cls, mock_pull, tmp_path):
    mock_client = MagicMock()
    mock_client.get_stack.return_value = {
        "name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0",
        "registry_ref": "ghcr.io/agentic-stacks/openstack:1.3.0"
    }
    mock_client_cls.return_value = mock_client
    mock_pull.return_value = "sha256:abc123"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry": "ghcr.io", "api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    runner.invoke(cli, ["pull", "agentic-stacks/openstack@1.3.0",
                         "--dir", str(tmp_path), "--config", str(config_path)])
    lock = yaml.safe_load((tmp_path / "stacks.lock").read_text())
    assert len(lock["stacks"]) == 1
    assert lock["stacks"][0]["name"] == "agentic-stacks/openstack"
    assert lock["stacks"][0]["digest"] == "sha256:abc123"


def test_pull_invalid_reference(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["pull", "invalid-ref", "--config", str(config_path)])
    assert result.exit_code != 0
