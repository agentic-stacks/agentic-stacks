import json
import shutil
import pytest
import yaml
from agentic_stacks.environments import (
    load_environment,
    list_environments,
    create_environment,
    validate_environment,
    StackEnvironmentError,
)


def test_load_environment(sample_environments_path):
    env = load_environment(sample_environments_path / "dev")
    assert env["name"] == "dev"
    assert env["profiles"]["networking"] == "option-a"


def test_load_missing_environment(sample_environments_path):
    with pytest.raises(StackEnvironmentError, match="not found"):
        load_environment(sample_environments_path / "nonexistent")


def test_list_environments(sample_environments_path):
    envs = list_environments(sample_environments_path)
    assert "dev" in envs


def test_create_environment(tmp_path):
    envs_dir = tmp_path / "environments"
    envs_dir.mkdir()
    env_data = {
        "name": "staging",
        "profiles": {"security": "baseline", "networking": "option-a", "storage": "default"},
        "approval": {"tier": "auto-notify"},
    }
    create_environment(envs_dir, "staging", env_data)
    assert (envs_dir / "staging" / "environment.yml").exists()
    loaded = yaml.safe_load((envs_dir / "staging" / "environment.yml").read_text())
    assert loaded["name"] == "staging"


def test_create_duplicate_environment_raises(tmp_path):
    envs_dir = tmp_path / "environments"
    envs_dir.mkdir()
    env_data = {"name": "dev", "profiles": {"security": "baseline"}}
    create_environment(envs_dir, "dev", env_data)
    with pytest.raises(StackEnvironmentError, match="already exists"):
        create_environment(envs_dir, "dev", env_data)


def test_validate_environment_valid(sample_stack_path):
    schema = json.loads((sample_stack_path / "environments" / "_schema.json").read_text())
    env = yaml.safe_load((sample_stack_path / "environments" / "dev" / "environment.yml").read_text())
    validate_environment(env, schema)


def test_validate_environment_invalid(sample_stack_path):
    schema = json.loads((sample_stack_path / "environments" / "_schema.json").read_text())
    env = {"name": "bad"}
    with pytest.raises(StackEnvironmentError, match="profiles"):
        validate_environment(env, schema)
