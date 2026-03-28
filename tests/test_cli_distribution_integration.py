# tests/test_cli_distribution_integration.py
"""Integration test: full publish/pull/search/upgrade CLI workflow with mocks."""
import yaml
import json
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_stack(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "integration-test", "namespace": "agentic-stacks", "version": "1.0.0",
        "description": "Integration test stack",
        "target": {"software": "test", "versions": ["1.0"]},
        "skills": [{"name": "deploy", "entry": "skills/deploy/", "description": "Deploy"}],
        "profiles": {"categories": ["security"], "path": "profiles/"},
        "environment_schema": "environments/_schema.json",
        "depends_on": [], "deprecations": [],
        "requires": {"tools": [], "python": ">=3.11"},
    }
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    (path / "skills").mkdir()
    (path / "skills" / "deploy").mkdir()
    (path / "profiles").mkdir()
    (path / "profiles" / "security").mkdir()
    (path / "environments").mkdir()
    (path / "environments" / "_schema.json").write_text(json.dumps({"type": "object"}))


@patch("agentic_stacks_cli.commands.publish.push_stack")
@patch("agentic_stacks_cli.commands.publish.RegistryClient")
@patch("agentic_stacks_cli.commands.pull.pull_stack")
@patch("agentic_stacks_cli.commands.pull.RegistryClient")
@patch("agentic_stacks_cli.commands.search.RegistryClient")
def test_publish_search_pull_workflow(
    mock_search_client_cls, mock_pull_client_cls, mock_pull_oci,
    mock_pub_client_cls, mock_push, tmp_path
):
    runner = CliRunner()
    stack_dir = tmp_path / "my-stack"
    _create_stack(stack_dir)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({
        "token": "ghp_test", "registry": "ghcr.io",
        "default_namespace": "agentic-stacks",
        "api_url": "https://example.com/api/v1",
    }))

    # 1. Publish
    mock_push.return_value = ("ghcr.io/agentic-stacks/integration-test:1.0.0", "sha256:abc")
    mock_pub_client = MagicMock()
    mock_pub_client.register_stack.return_value = {"status": "ok"}
    mock_pub_client_cls.return_value = mock_pub_client

    result = runner.invoke(cli, ["publish", "--path", str(stack_dir), "--config", str(config_path)])
    assert result.exit_code == 0

    # 2. Search
    mock_search = MagicMock()
    mock_search.search.return_value = [
        {"name": "integration-test", "namespace": "agentic-stacks",
         "version": "1.0.0", "description": "Integration test stack"}
    ]
    mock_search_client_cls.return_value = mock_search

    result = runner.invoke(cli, ["search", "integration", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "integration-test" in result.output

    # 3. Pull
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    mock_pull_client = MagicMock()
    mock_pull_client.get_stack.return_value = {
        "name": "integration-test", "namespace": "agentic-stacks", "version": "1.0.0",
        "registry_ref": "ghcr.io/agentic-stacks/integration-test:1.0.0"
    }
    mock_pull_client_cls.return_value = mock_pull_client
    mock_pull_oci.return_value = "sha256:abc"

    result = runner.invoke(cli, ["pull", "agentic-stacks/integration-test@1.0.0",
                                  "--dir", str(project_dir), "--config", str(config_path)])
    assert result.exit_code == 0

    # 4. Verify lock file
    lock = yaml.safe_load((project_dir / "stacks.lock").read_text())
    assert lock["stacks"][0]["name"] == "agentic-stacks/integration-test"
