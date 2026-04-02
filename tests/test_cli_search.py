import pathlib
from unittest.mock import patch
from click.testing import CliRunner
import yaml

from agentic_stacks_cli import cli

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "registry"


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_by_name(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "openstack", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "openstack-kolla" in result.output


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_by_target(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "talos-linux", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "kubernetes-talos" in result.output


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_by_skill(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "RAID", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "hardware-dell" in result.output


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_no_results(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "zzz-nonexistent", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "No stacks found" in result.output


@patch("agentic_stacks_cli.commands.search.ensure_registry")
def test_search_shows_description(mock_ensure, tmp_path):
    mock_ensure.return_value = FIXTURES
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "dell", "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "hardware-dell" in result.output


def test_search_no_query():
    runner = CliRunner()
    result = runner.invoke(cli, ["search"])
    assert result.exit_code != 0
