"""Environment CRUD and schema validation."""

import pathlib
import yaml
from agentic_stacks.schema import validate_against_schema, ValidationError


class EnvironmentError(Exception):
    pass


def load_environment(env_dir: pathlib.Path) -> dict:
    env_dir = pathlib.Path(env_dir)
    env_file = env_dir / "environment.yml"
    if not env_file.exists():
        raise EnvironmentError(f"Environment not found: {env_dir}")
    with open(env_file) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise EnvironmentError(f"Environment must be a YAML mapping: {env_file}")
    return data


def list_environments(environments_dir: pathlib.Path) -> list[str]:
    environments_dir = pathlib.Path(environments_dir)
    if not environments_dir.exists():
        return []
    return sorted(
        d.name for d in environments_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "environment.yml").exists()
    )


def create_environment(environments_dir: pathlib.Path, name: str, data: dict) -> pathlib.Path:
    environments_dir = pathlib.Path(environments_dir)
    env_dir = environments_dir / name
    if env_dir.exists():
        raise EnvironmentError(f"Environment already exists: {env_dir}")
    env_dir.mkdir(parents=True)
    env_file = env_dir / "environment.yml"
    with open(env_file, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    return env_dir


def validate_environment(data: dict, schema: dict) -> None:
    try:
        validate_against_schema(data, schema)
    except ValidationError as e:
        raise EnvironmentError(str(e)) from e
