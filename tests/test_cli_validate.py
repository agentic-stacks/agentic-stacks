import json
import yaml
from click.testing import CliRunner
from agentic_stacks_cli import cli


def _setup_stack_with_env(path, env_name="dev", env_data=None):
    path.mkdir(parents=True, exist_ok=True)
    manifest = {"name": "test", "namespace": "testorg", "version": "1.0.0", "description": "Test", "environment_schema": "environments/_schema.json"}
    (path / "stack.yaml").write_text(yaml.dump(manifest, sort_keys=False))
    envs = path / "environments"
    envs.mkdir(exist_ok=True)
    schema = {"$schema": "http://json-schema.org/draft-07/schema#", "type": "object", "required": ["name", "profiles"], "properties": {"name": {"type": "string"}, "profiles": {"type": "object"}}}
    (envs / "_schema.json").write_text(json.dumps(schema, indent=2))
    env_dir = envs / env_name
    env_dir.mkdir(exist_ok=True)
    if env_data is None:
        env_data = {"name": env_name, "profiles": {"security": "baseline"}}
    (env_dir / "environment.yml").write_text(yaml.dump(env_data, sort_keys=False))


def test_validate_valid_environment(tmp_path):
    _setup_stack_with_env(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "dev", "--path", str(tmp_path / "stack")])
    assert result.exit_code == 0
    assert "valid" in result.output.lower()


def test_validate_invalid_environment(tmp_path):
    _setup_stack_with_env(tmp_path / "stack", env_data={"name": "dev"})
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "dev", "--path", str(tmp_path / "stack")])
    assert result.exit_code != 0
    assert "profiles" in result.output.lower()


def test_validate_missing_environment(tmp_path):
    _setup_stack_with_env(tmp_path / "stack")
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "nonexistent", "--path", str(tmp_path / "stack")])
    assert result.exit_code != 0


def test_validate_list_environments(tmp_path):
    _setup_stack_with_env(tmp_path / "stack", env_name="dev")
    staging_dir = tmp_path / "stack" / "environments" / "staging"
    staging_dir.mkdir(exist_ok=True)
    (staging_dir / "environment.yml").write_text(yaml.dump({"name": "staging", "profiles": {"security": "hardened"}}, sort_keys=False))
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--list", "--path", str(tmp_path / "stack")])
    assert result.exit_code == 0
    assert "dev" in result.output
    assert "staging" in result.output
