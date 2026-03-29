"""agentic-stacks create — scaffold a new stack."""

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


def _parse_identity(identity: str) -> tuple[str, str]:
    """Parse 'owner/name' into (owner, name)."""
    if "/" not in identity:
        raise click.BadParameter(
            f"Expected owner/name format (e.g., my-org/my-stack), got: {identity}",
            param_hint="'IDENTITY'",
        )
    owner, name = identity.split("/", 1)
    if not owner or not name:
        raise click.BadParameter(
            f"Both owner and name are required (e.g., my-org/my-stack), got: {identity}",
            param_hint="'IDENTITY'",
        )
    return owner, name


@click.command()
@click.argument("identity")
@click.argument("path", required=False, default=None, type=click.Path())
def create(identity: str, path: str | None):
    """Create a new stack.

    IDENTITY is owner/name (e.g., my-org/my-stack).
    PATH is where to create it (default: ./name).
    """
    owner, name = _parse_identity(identity)

    if path is None:
        stack_dir = pathlib.Path(f"./{name}")
    else:
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
        "owner": owner,
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

    claude_md = (
        f"# {name}\n\n"
        f"Stack: {owner}/{name}\n\n"
        f"## Authoring Guide\n\n"
        f"Follow the stack authoring guide to build this stack:\n"
        f"https://github.com/agentic-stacks/agentic-stacks/blob/main/docs/guides/authoring-a-stack.md\n\n"
        f"Run `agentic-stacks doctor` to validate.\n"
    )
    (stack_dir / "CLAUDE.md").write_text(claude_md)

    click.echo(f"Created stack '{owner}/{name}' at {stack_dir}")
