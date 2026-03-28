"""astack init — scaffold a new stack project."""

import json
import pathlib

import click
import yaml


PROFILE_CATEGORIES = ["security", "networking", "storage", "scale", "features"]

DEFAULT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "profiles"],
    "properties": {
        "name": {"type": "string"},
        "description": {"type": "string"},
        "profiles": {"type": "object"},
        "approval": {
            "type": "object",
            "properties": {
                "tier": {
                    "type": "string",
                    "enum": ["auto", "auto-notify", "human-approve"],
                }
            },
        },
    },
}


@click.command()
@click.argument("path", type=click.Path())
@click.option("--name", required=True, help="Stack name")
@click.option("--namespace", required=True, help="Stack namespace (e.g., org name)")
def init(path: str, name: str, namespace: str):
    """Scaffold a new stack project."""
    stack_dir = pathlib.Path(path)

    if stack_dir.exists() and any(stack_dir.iterdir()):
        raise click.ClickException(f"Directory already exists and is not empty: {stack_dir}")

    stack_dir.mkdir(parents=True, exist_ok=True)

    (stack_dir / "skills").mkdir()
    (stack_dir / "src").mkdir()
    (stack_dir / "overrides").mkdir()

    profiles_dir = stack_dir / "profiles"
    profiles_dir.mkdir()
    for category in PROFILE_CATEGORIES:
        (profiles_dir / category).mkdir()

    envs_dir = stack_dir / "environments"
    envs_dir.mkdir()

    manifest = {
        "name": name,
        "namespace": namespace,
        "version": "0.1.0",
        "description": f"{name} stack",
        "target": {"software": name, "versions": []},
        "skills": [],
        "profiles": {
            "categories": PROFILE_CATEGORIES,
            "path": "profiles/",
            "merge_order": "security first (enforced), then declared order",
        },
        "environment_schema": "environments/_schema.json",
        "depends_on": [],
        "requires": {"tools": [], "python": ">=3.11"},
        "deprecations": [],
    }
    with open(stack_dir / "stack.yaml", "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    with open(envs_dir / "_schema.json", "w") as f:
        json.dump(DEFAULT_SCHEMA, f, indent=2)
        f.write("\n")

    claude_md = f"# {name}\n\nStack: {namespace}/{name}\n\nRun `astack doctor` to validate.\n"
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Initialized stack '{namespace}/{name}' at {stack_dir}")
