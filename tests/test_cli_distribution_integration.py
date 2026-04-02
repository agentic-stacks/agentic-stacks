# tests/test_cli_distribution_integration.py
"""Integration test: full publish/pull/search CLI workflow with mocks."""
import yaml
import json
from unittest.mock import patch
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_stack(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "integration-test", "owner": "agentic-stacks", "version": "1.0.0",
        "description": "Integration test stack",
        "repository": "https://github.com/agentic-stacks/integration-test",
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


@patch("agentic_stacks_cli.commands.publish.ensure_registry")
@patch("agentic_stacks_cli.commands.pull._clone_or_pull")
def test_publish_pull_workflow(mock_clone, mock_ensure, tmp_path):
    runner = CliRunner()
    stack_dir = tmp_path / "my-stack"
    _create_stack(stack_dir)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))

    mock_ensure.return_value = tmp_path / "registry"

    # 1. Publish — generates formula
    result = runner.invoke(cli, ["publish", "--path", str(stack_dir), "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "published" in result.output.lower()
    assert (stack_dir / "formula.yaml").exists()

    # 2. Pull — git clones into .stacks/
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    result = runner.invoke(cli, ["pull", "agentic-stacks/integration-test",
                                  "--path", str(project_dir), "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    mock_clone.assert_called_once_with(
        "https://github.com/agentic-stacks/integration-test",
        project_dir / ".stacks" / "integration-test",
    )

    # 3. Verify lock file
    lock = yaml.safe_load((project_dir / "stacks.lock").read_text())
    assert lock["stacks"][0]["name"] == "agentic-stacks/integration-test"
    assert lock["stacks"][0]["repository"] == "https://github.com/agentic-stacks/integration-test"
