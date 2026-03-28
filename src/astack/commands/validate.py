"""astack validate — validate an environment against its schema."""

import json
import pathlib

import click

from agentic_stacks.manifest import load_manifest, ManifestError
from agentic_stacks.environments import (
    load_environment,
    list_environments,
    validate_environment,
    EnvironmentError,
)


@click.command()
@click.argument("environment", required=False)
@click.option("--path", type=click.Path(exists=True), default=".", help="Path to stack directory")
@click.option("--list", "list_envs", is_flag=True, help="List available environments")
def validate(environment: str | None, path: str, list_envs: bool):
    """Validate an environment against the stack schema."""
    stack_dir = pathlib.Path(path)

    try:
        manifest = load_manifest(stack_dir / "stack.yaml")
    except ManifestError as e:
        raise click.ClickException(f"Cannot load manifest: {e}")

    envs_dir = stack_dir / "environments"

    if list_envs:
        envs = list_environments(envs_dir)
        if not envs:
            click.echo("No environments found.")
        else:
            click.echo("Environments:")
            for env_name in envs:
                click.echo(f"  - {env_name}")
        return

    if not environment:
        raise click.ClickException("Specify an environment name, or use --list to see available environments.")

    try:
        env_data = load_environment(envs_dir / environment)
    except EnvironmentError as e:
        raise click.ClickException(str(e))

    schema_path_str = manifest.get("environment_schema", "")
    if not schema_path_str:
        raise click.ClickException("No environment_schema defined in stack.yaml")

    schema_file = stack_dir / schema_path_str
    if not schema_file.exists():
        raise click.ClickException(f"Schema file not found: {schema_path_str}")

    try:
        schema = json.loads(schema_file.read_text())
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid schema JSON: {e}")

    try:
        validate_environment(env_data, schema)
    except EnvironmentError as e:
        raise click.ClickException(f"Environment '{environment}' is invalid:\n{e}")

    click.echo(f"Environment '{environment}' is valid.")
