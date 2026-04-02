import json
import yaml
from unittest.mock import patch
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _create_publishable_stack(path):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test-stack", "owner": "agentic-stacks", "version": "1.0.0",
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


@patch("agentic_stacks_cli.commands.publish.ensure_registry")
def test_publish_success(mock_ensure, tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    mock_ensure.return_value = tmp_path / "registry"
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code == 0, result.output
    assert "published" in result.output.lower()
    # Check formula was written
    formula_path = tmp_path / "stack" / "formula.yaml"
    assert formula_path.exists()
    formula = yaml.safe_load(formula_path.read_text())
    assert formula["name"] == "test-stack"
    assert formula["owner"] == "agentic-stacks"
    # Check formula written to registry cache
    cached = tmp_path / "registry" / "stacks" / "agentic-stacks" / "test-stack.yaml"
    assert cached.exists()


def test_publish_no_repository_fails(tmp_path):
    _create_publishable_stack(tmp_path / "stack")
    manifest = yaml.safe_load((tmp_path / "stack" / "stack.yaml").read_text())
    manifest.pop("repository")
    (tmp_path / "stack" / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code != 0
    assert "repository" in result.output.lower()


def test_publish_invalid_stack_fails(tmp_path):
    (tmp_path / "stack").mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({}))
    runner = CliRunner()
    result = runner.invoke(cli, ["publish", "--path", str(tmp_path / "stack"),
                                  "--config", str(config_path)])
    assert result.exit_code != 0
