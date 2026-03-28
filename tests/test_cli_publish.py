import yaml
import json
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_publishable_stack(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test-stack", "namespace": "agentic-stacks", "version": "1.0.0",
        "description": "A test stack",
        "target": {"software": "test", "versions": ["1.0"]},
        "skills": [{"name": "deploy", "entry": "skills/deploy/", "description": "Deploy"}],
        "profiles": {"categories": ["security"], "path": "profiles/"},
        "environment_schema": "environments/_schema.json",
        "depends_on": [], "deprecations": [],
        "requires": {"tools": ["test-tool"], "python": ">=3.11"},
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "skills").mkdir(); (path / "skills" / "deploy").mkdir()
    (path / "profiles").mkdir(); (path / "profiles" / "security").mkdir()
    (path / "environments").mkdir()
    (path / "environments" / "_schema.json").write_text(json.dumps({"type": "object"}))


@patch("agentic_stacks_cli.commands.publish.push_stack")
@patch("agentic_stacks_cli.commands.publish.RegistryClient")
def test_publish_success(mock_client_cls, mock_push, tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"token": "ghp_test", "registry": "ghcr.io",
                                       "default_namespace": "agentic-stacks",
                                       "api_url": "https://example.com/api/v1"}))
    mock_push.return_value = ("ghcr.io/agentic-stacks/test-stack:1.0.0", "sha256:abc123")
    mock_client = MagicMock()
    mock_client.register_stack.return_value = {"status": "registered"}
    mock_client_cls.return_value = mock_client
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"), "--config", str(config_path)])
    assert result.exit_code == 0
    assert "published" in result.output.lower() or "ghcr.io" in result.output
    mock_push.assert_called_once()
    mock_client.register_stack.assert_called_once()


@patch("agentic_stacks_cli.commands.publish.push_stack")
@patch("agentic_stacks_cli.commands.publish.RegistryClient")
def test_publish_no_token_fails(mock_client_cls, mock_push, tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"registry": "ghcr.io", "api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"), "--config", str(config_path)])
    assert result.exit_code != 0
    assert "login" in result.output.lower() or "token" in result.output.lower()


def test_publish_invalid_stack_fails(tmp_path):
    (tmp_path / "stack").mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"token": "ghp_test"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"), "--config", str(config_path)])
    assert result.exit_code != 0
