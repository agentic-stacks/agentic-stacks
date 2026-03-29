import json
import yaml
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_publishable_stack(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test-stack", "namespace": "agentic-stacks", "version": "1.0.0",
        "description": "A test stack",
        "repository": "https://github.com/agentic-stacks/test-stack",
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


@patch("agentic_stacks_cli.commands.publish.RegistryClient")
def test_publish_success(mock_client_cls, tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "token": "ghp_test",
        "api_url": "https://example.com/api/v1",
    }))
    mock_client = MagicMock()
    mock_client.register_stack.return_value = {"status": "registered"}
    mock_client_cls.return_value = mock_client
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "published" in result.output.lower()
    mock_client.register_stack.assert_called_once()
    call_data = mock_client.register_stack.call_args[0][0]
    assert call_data["registry_ref"] == "https://github.com/agentic-stacks/test-stack"


def test_publish_no_token_fails(tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code != 0
    assert "login" in result.output.lower()


def test_publish_no_repository_fails(tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    # Remove repository field
    manifest = yaml.safe_load((tmp_path / "stack" / "stack.yaml").read_text())
    manifest.pop("repository")
    (tmp_path / "stack" / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"token": "ghp_test",
                                       "api_url": "https://example.com/api/v1"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code != 0
    assert "repository" in result.output.lower()


def test_publish_invalid_stack_fails(tmp_path):
    (tmp_path / "stack").mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"token": "ghp_test"}))
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code != 0
