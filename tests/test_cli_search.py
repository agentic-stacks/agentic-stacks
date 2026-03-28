import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli


@patch("agentic_stacks_cli.commands.search.RegistryClient")
def test_search_shows_results(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_client.search.return_value = [
        {"name": "openstack", "namespace": "agentic-stacks", "version": "1.3.0", "description": "OpenStack deployment"},
        {"name": "kubernetes", "namespace": "agentic-stacks", "version": "2.1.0", "description": "Kubernetes on Talos"},
    ]
    mock_client_cls.return_value = mock_client
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "stack", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "openstack" in result.output
    assert "kubernetes" in result.output


@patch("agentic_stacks_cli.commands.search.RegistryClient")
def test_search_no_results(mock_client_cls, tmp_path):
    mock_client = MagicMock()
    mock_client.search.return_value = []
    mock_client_cls.return_value = mock_client
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "nonexistent", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "no stacks found" in result.output.lower() or "0" in result.output


def test_search_no_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["search"])
    assert result.exit_code != 0
